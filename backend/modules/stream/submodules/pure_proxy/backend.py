import asyncio
import logging
import time
import os
import shutil
import aiohttp
import socket
import struct
from urllib.parse import urlparse
from typing import Dict, Optional, List

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

logger = logging.getLogger(__name__)


class ProxySession:
    """Активная сессия проксирования с фоновой буферизацией и реал-тайм очередями."""

    def __init__(self, task_id: str, task: StreamTask, settings: dict):
        self.task_id = task_id
        self.task = task
        self.settings = settings
        self.started_at = time.time()
        
        # Настройки из манифеста (с префиксом pure_proxy_)
        if task.output_type == OutputType.HLS:
            self.segment_duration = int(settings.get("pure_proxy_hls_segment_duration", 5))
            self.max_segments = int(settings.get("pure_proxy_hls_max_segments", 24))
        else:
            # Для HTTP_TS и прочих буферизированных режимов
            self.segment_duration = int(settings.get("pure_proxy_http_ts_segment_duration", 5))
            self.max_segments = int(settings.get("pure_proxy_http_ts_max_segments", 24))
        
        # Директория для буфера
        self.buffer_dir = f"/opt/nms-webui/data/streams/proxy-{task_id}"
        self.segments: List[str] = []
        
        # Флаг: нужно ли писать на диск (включается при http_ts или hls)
        self.buffering_enabled = (task.output_type in {OutputType.HTTP_TS, OutputType.HLS})
        
        # Подписчики на реал-тайм поток (для обычного HTTP)
        self._subscribers: List[asyncio.Queue] = []
        
        self._writer_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._current_file = None
        self._seg_idx = 0
        self._seg_start_time = 0

    def start(self):
        """Запуск фонового чтения."""
        if self._writer_task:
            return
        self._writer_task = asyncio.create_task(self._run_writer())
        logger.info(f"ProxySession {self.task_id}: фоновое чтение запущено "
                    f"(buffering={self.buffering_enabled}, seg={self.segment_duration}s)")

    def enable_buffering(self):
        """Включить запись на диск (если еще не включена)."""
        if not self.buffering_enabled:
            logger.info(f"ProxySession {self.task_id}: включена запись буфера на диск")
            if os.path.exists(self.buffer_dir):
                shutil.rmtree(self.buffer_dir)
            os.makedirs(self.buffer_dir, exist_ok=True)
            self.buffering_enabled = True

    def subscribe(self) -> asyncio.Queue:
        """Подписаться на получение чанков в реальном времени."""
        queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Отписаться."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def stop(self):
        """Остановка и очистка."""
        self._stop_event.set()
        if self._writer_task:
            self._writer_task.cancel()
        
        # Очистка файлов
        try:
            if os.path.exists(self.buffer_dir):
                shutil.rmtree(self.buffer_dir)
        except: pass

    async def _run_writer(self):
        url = self.task.input_url
        protocol = self.task.input_protocol
        try:
            if protocol == StreamProtocol.HTTP:
                await self._write_http(url)
            elif protocol == StreamProtocol.UDP:
                await self._write_udp(url)
            elif protocol == StreamProtocol.HLS:
                await self._write_hls(url)
        except asyncio.CancelledError: pass
        except Exception as e:
            logger.error(f"ProxyWriter {self.task_id} error: {e}")
        finally:
            await self._close_current_file()

    async def _write_hls(self, url):
        """Чтение HLS плейлиста и последовательная загрузка сегментов."""
        from urllib.parse import urljoin
        
        timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=60)
        downloaded_segments = set()
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while not self._stop_event.is_set():
                try:
                    async with session.get(url) as response:
                        if response.status >= 400:
                            await asyncio.sleep(2); continue
                        
                        text = await response.text()
                        lines = text.splitlines()
                        is_master = any(line.startswith("#EXT-X-STREAM-INF") for line in lines)
                        
                        if is_master:
                            for i, line in enumerate(lines):
                                if line.startswith("#EXT-X-STREAM-INF") and i + 1 < len(lines):
                                    variant_url = lines[i+1].strip()
                                    if not variant_url.startswith("#"):
                                        url = urljoin(url, variant_url)
                                        break
                            await asyncio.sleep(0.1); continue
                        
                        segments_to_load = []
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if line.startswith("#EXTINF") and i + 1 < len(lines):
                                segment_url = lines[i+1].strip()
                                if not segment_url.startswith("#"):
                                    full_url = urljoin(url, segment_url)
                                    if full_url not in downloaded_segments:
                                        segments_to_load.append(full_url)
                        
                        if not segments_to_load:
                            await asyncio.sleep(1); continue
                            
                        for seg_url in segments_to_load:
                            if self._stop_event.is_set(): break
                            
                            try:
                                async with session.get(seg_url) as seg_resp:
                                    if seg_resp.status == 200:
                                        data = await seg_resp.read()
                                        await self._process_chunk(data)
                                        downloaded_segments.add(seg_url)
                                        if len(downloaded_segments) > 100:
                                            downloaded_segments = set(list(downloaded_segments)[-50:])
                            except Exception as e:
                                logger.error(f"HLS segment download error: {e}")
                                await asyncio.sleep(0.5)
                        
                        await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"HLS playlist error: {e}")
                    await asyncio.sleep(2)

    async def _process_chunk(self, chunk: bytes):
        """Общая логика обработки чанка (рассылка + запись)."""
        if not hasattr(self, '_synced'): self._synced = False
        
        if not self._synced:
            idx = chunk.find(b'\x47')
            if idx != -1:
                chunk = chunk[idx:]; self._synced = True
            else: return

        # 1. Рассылка подписчикам
        for q in self._subscribers:
            try:
                if q.full(): q.get_nowait()
                q.put_nowait(chunk)
            except: pass

        # 2. Запись на диск
        if self.buffering_enabled:
            await self._write_to_buffer(chunk)
    async def _write_to_buffer(self, chunk: bytes):
        now = time.time()
        if not self._current_file or (now - self._seg_start_time) >= self.segment_duration:
            await self._rotate_segment(now)
        
        if self._current_file:
            await asyncio.to_thread(self._sync_write, chunk)

    def _sync_write(self, chunk: bytes):
        if self._current_file:
            try:
                self._current_file.write(chunk)
                self._current_file.flush()
            except Exception as e:
                logger.error(f"Sync write error: {e}")

    async def _rotate_segment(self, now):
        """Смена сегмента: закрываем старый, открываем новый."""
        old_file = self._current_file
        old_seg_name = f"seg_{self._seg_idx - 1}.ts" if self._seg_idx > 0 else None
        
        await self._close_current_file()
        
        # Только после закрытия добавляем старый сегмент в список доступных
        if old_file and old_seg_name:
            self.segments.append(old_seg_name)
            if len(self.segments) > self.max_segments:
                old_to_del = self.segments.pop(0)
                old_path = os.path.join(self.buffer_dir, old_to_del)
                await asyncio.to_thread(self._sync_delete, old_path)

        try:
            if not os.path.exists(self.buffer_dir):
                os.makedirs(self.buffer_dir, exist_ok=True)
            
            new_seg_name = f"seg_{self._seg_idx}.ts"
            full_path = os.path.join(self.buffer_dir, new_seg_name)
            
            self._current_file = open(full_path, "wb")
            self._seg_idx += 1
            self._seg_start_time = now
        except Exception as e:
            logger.error(f"Segment rotation error: {e}")

    def _sync_delete(self, path):
        try:
            if os.path.exists(path): os.remove(path)
        except: pass

    async def _close_current_file(self):
        if self._current_file:
            f = self._current_file
            self._current_file = None
            await asyncio.to_thread(f.close)

    async def _write_http(self, url):
        timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status >= 400: return
                await self._streaming_loop(response.content)

    async def _write_udp(self, url):
        parsed = urlparse(url)
        host = parsed.hostname or "0.0.0.0"
        port = parsed.port or 1234
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            try: sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except: pass
        sock.bind((host, port))
        
        first_octet = int(host.split('.')[0]) if host.split('.')[0].isdigit() else 0
        if 224 <= first_octet <= 239:
            membership = struct.pack("4sl", socket.inet_aton(host), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)

        sock.setblocking(False)
        loop = asyncio.get_running_loop()
        
        async def udp_it():
            while not self._stop_event.is_set():
                try:
                    data = await loop.sock_recv(sock, 65536)
                    if not data: break
                    yield data
                except: break
        try: await self._streaming_loop(udp_it())
        finally: sock.close()

    async def _streaming_loop(self, iterator):
        source = iterator.iter_chunks() if hasattr(iterator, 'iter_chunks') else iterator
        try:
            async for chunk_data in source:
                chunk = chunk_data[0] if isinstance(chunk_data, tuple) else chunk_data
                if self._stop_event.is_set(): break
                await self._process_chunk(chunk)
        except Exception as e:
            logger.error(f"ProxyWriter {self.task_id} loop error: {e}")


class PureProxyStreamer:
    """Нативный прокси с поддержкой 2-минутной буферизации и переиспользования сессий."""

    def __init__(self, settings: dict):
        self.settings = settings
        self._sessions: Dict[str, ProxySession] = {}     # master_task_id -> session
        self._url_to_session: Dict[str, str] = {}        # url -> master_task_id
        self._task_to_session: Dict[str, str] = {}       # client_task_id -> master_task_id

    async def start(self, task: StreamTask) -> StreamResult:
        url = task.input_url
        client_id = task.task_id or f"p{int(time.time())}"
        
        # Проверяем, есть ли уже активная сессия для этого URL
        master_id = self._url_to_session.get(url)
        if master_id and master_id in self._sessions:
            session = self._sessions[master_id]
            logger.info(f"PureProxy: переиспользуем сессию '{master_id}' для клиента {client_id}")
            self._task_to_session[client_id] = master_id
            return self._make_result(client_id, session)

        # Создаем новую мастер-сессию
        session = ProxySession(task_id=client_id, task=task, settings=self.settings)
        session.start()
        
        self._sessions[client_id] = session
        self._url_to_session[url] = client_id
        self._task_to_session[client_id] = client_id

        return self._make_result(client_id, session)

    def _make_result(self, task_id: str, session: ProxySession) -> StreamResult:
        output_url = f"/api/modules/stream/v1/proxy/{task_id}"
        if session.task.output_type == OutputType.HLS:
            output_url = f"{output_url}/index.m3u8"

        return StreamResult(
            task_id=task_id,
            success=True,
            backend_used="pure_proxy",
            output_url=output_url,
            metadata={
                "type": "buffered_proxy",
                "buffer_dir": session.buffer_dir,
                "protocol": session.task.input_protocol.value,
                "segments_count": len(session.segments)
            }
        )

    async def stop(self, task_id: str) -> bool:
        # Убираем маппинг клиента
        master_id = self._task_to_session.pop(task_id, None)
        if not master_id:
            return False
            
        # Если это был последний клиент мастер-сессии, останавливаем её
        # Для простоты: если task_id == master_id, значит это "владелец" сессии.
        # Но в Shared Buffer лучше считать ссылки. 
        # Пока будем останавливать только если это был реальный владелец:
        if task_id == master_id:
            session = self._sessions.pop(master_id, None)
            if session:
                url = session.task.input_url
                if self._url_to_session.get(url) == master_id:
                    self._url_to_session.pop(url, None)
                session.stop()
                return True
        return True

    def get_session(self, task_id: str) -> Optional[ProxySession]:
        master_id = self._task_to_session.get(task_id)
        if master_id:
            return self._sessions.get(master_id)
        return None

    def get_active_count(self) -> int:
        return len(self._sessions)
