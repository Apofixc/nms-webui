# Бэкенд Builtin Proxy — стриминг через прямое проксирование.
# Читает данные из источника (HTTP/UDP/HLS) и раздаёт
# подписчикам через BufferedSession с дисковой буферизацией.
import asyncio
import logging
import time
import os
import aiohttp
import socket
import struct
from urllib.parse import urlparse
from typing import Dict, Optional

from backend.modules.stream.core.interfaces import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    BufferedSession,
)

logger = logging.getLogger(__name__)


class ProxySession(BufferedSession):
    """Активная сессия проксирования с фоновой буферизацией.

    Наследует BufferedSession — общую логику TS-синхронизации,
    pub/sub для подписчиков и сегментированной записи на диск.
    
    В отличие от VLC/Astra, мост живёт внутри сессии,
    т.к. нет внешнего процесса — прокси читает напрямую.
    """

    def __init__(self, task_id: str, task: StreamTask, settings: dict):
        # Определяем параметры сегментации из настроек
        if task.output_type == OutputType.HLS:
            seg_dur = int(settings.get("builtin_proxy_hls_segment_duration", 5))
            max_seg = int(settings.get("builtin_proxy_hls_max_segments", 24))
        else:
            seg_dur = int(settings.get("builtin_proxy_http_ts_segment_duration", 5))
            max_seg = int(settings.get("builtin_proxy_http_ts_max_segments", 24))

        buffer_dir = f"data/streams/proxy-{task_id}"

        super().__init__(
            task_id=task_id,
            task=task,
            buffer_dir=buffer_dir,
            segment_duration=seg_dur,
            max_segments=max_seg,
        )

        self._settings = settings
        self._bridge_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    # ── Жизненный цикл ──────────────────────────────────────────────────

    def start(self):
        """Запуск фонового чтения."""
        if self._bridge_task:
            return
        self._bridge_task = asyncio.create_task(self._run_bridge())
        logger.info(
            f"BuiltinProxy [{self.task_id}]: фоновое чтение запущено "
            f"(buffering={self.buffering_enabled}, seg={self.segment_duration}s)"
        )

    def stop(self):
        """Остановка сессии.
        
        ВАЖНО: НЕ удаляет временные файлы — это задача модуля Stream.
        """
        self._stop_event.set()
        if self._bridge_task:
            self._bridge_task.cancel()
        self.close()

    # ── Мост данных ─────────────────────────────────────────────────────

    async def _run_bridge(self):
        """Фоновая задача чтения из источника."""
        url = self.task.input_url
        protocol = self.task.input_protocol
        try:
            if protocol == StreamProtocol.HTTP:
                await self._write_http(url)
            elif protocol == StreamProtocol.UDP:
                await self._write_udp(url)
            elif protocol == StreamProtocol.HLS:
                await self._write_hls(url)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"BuiltinProxy [{self.task_id}]: ошибка моста {e}")
        finally:
            await self._close_current_file()

    # ── Протоколо-специфичная логика чтения ─────────────────────────────

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
                            await asyncio.sleep(2)
                            continue
                        
                        text = await response.text()
                        lines = text.splitlines()
                        is_master = any(
                            line.startswith("#EXT-X-STREAM-INF") for line in lines
                        )
                        
                        if is_master:
                            for i, line in enumerate(lines):
                                if (
                                    line.startswith("#EXT-X-STREAM-INF")
                                    and i + 1 < len(lines)
                                ):
                                    variant_url = lines[i + 1].strip()
                                    if not variant_url.startswith("#"):
                                        url = urljoin(url, variant_url)
                                        break
                            await asyncio.sleep(0.1)
                            continue
                        
                        segments_to_load = []
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if line.startswith("#EXTINF") and i + 1 < len(lines):
                                segment_url = lines[i + 1].strip()
                                if not segment_url.startswith("#"):
                                    full_url = urljoin(url, segment_url)
                                    if full_url not in downloaded_segments:
                                        segments_to_load.append(full_url)
                        
                        if not segments_to_load:
                            await asyncio.sleep(1)
                            continue
                            
                        for seg_url in segments_to_load:
                            if self._stop_event.is_set():
                                break
                            
                            try:
                                async with session.get(seg_url) as seg_resp:
                                    if seg_resp.status == 200:
                                        data = await seg_resp.read()
                                        await self.process_chunk(data)
                                        downloaded_segments.add(seg_url)
                                        if len(downloaded_segments) > 100:
                                            downloaded_segments = set(
                                                list(downloaded_segments)[-50:]
                                            )
                            except Exception as e:
                                logger.error(
                                    f"BuiltinProxy [{self.task_id}]: "
                                    f"ошибка HLS-сегмента {e}"
                                )
                                await asyncio.sleep(0.5)
                        
                        await asyncio.sleep(1)
                except Exception as e:
                    logger.error(
                        f"BuiltinProxy [{self.task_id}]: "
                        f"ошибка HLS-плейлиста {e}"
                    )
                    await asyncio.sleep(2)

    async def _write_http(self, url):
        """Чтение из HTTP источника."""
        timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status >= 400:
                    return
                await self._streaming_loop(response.content)

    async def _write_udp(self, url):
        """Чтение из UDP источника."""
        parsed = urlparse(url)
        host = parsed.hostname or "0.0.0.0"
        port = parsed.port or 1234
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except Exception:
                pass
        sock.bind((host, port))
        
        first_octet = int(host.split('.')[0]) if host.split('.')[0].isdigit() else 0
        if 224 <= first_octet <= 239:
            membership = struct.pack(
                "4sl", socket.inet_aton(host), socket.INADDR_ANY
            )
            sock.setsockopt(
                socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership
            )

        sock.setblocking(False)
        loop = asyncio.get_running_loop()
        
        async def udp_it():
            while not self._stop_event.is_set():
                try:
                    data = await loop.sock_recv(sock, 65536)
                    if not data:
                        break
                    yield data
                except Exception:
                    break
        try:
            await self._streaming_loop(udp_it())
        finally:
            sock.close()

    async def _streaming_loop(self, iterator):
        """Универсальный цикл чтения из источника."""
        source = (
            iterator.iter_chunks()
            if hasattr(iterator, 'iter_chunks')
            else iterator
        )
        try:
            async for chunk_data in source:
                chunk = (
                    chunk_data[0]
                    if isinstance(chunk_data, tuple)
                    else chunk_data
                )
                if self._stop_event.is_set():
                    break
                await self.process_chunk(chunk)
        except Exception as e:
            logger.error(
                f"BuiltinProxy [{self.task_id}]: ошибка цикла чтения {e}"
            )


class BuiltinProxyStreamer:
    """Встроенный прокси с буферизацией и переиспользованием сессий.

    Для каждого запроса:
    1. Проверяет, есть ли уже сессия для данного URL.
    2. Если да — переиспользует (разделяет подписчиков).
    3. Если нет — создаёт новую ProxySession.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._sessions: Dict[str, ProxySession] = {}      # master_task_id -> session
        self._url_to_session: Dict[str, str] = {}         # url -> master_task_id
        self._task_to_session: Dict[str, str] = {}        # client_task_id -> master_task_id

    # ── Жизненный цикл потока ───────────────────────────────────────────

    async def start(self, task: StreamTask) -> StreamResult:
        """Запуск проксирования (или переиспользование существующей сессии)."""
        url = task.input_url
        client_id = task.task_id or f"p{int(time.time())}"
        
        # Проверяем, есть ли уже активная сессия для этого URL
        master_id = self._url_to_session.get(url)
        if master_id and master_id in self._sessions:
            session = self._sessions[master_id]
            logger.info(
                f"BuiltinProxy [{client_id}]: "
                f"переиспользование сессии '{master_id}'"
            )
            self._task_to_session[client_id] = master_id
            return self._make_result(client_id, session)

        # Создаем новую мастер-сессию
        session = ProxySession(
            task_id=client_id, task=task, settings=self._settings
        )
        session.start()
        
        self._sessions[client_id] = session
        self._url_to_session[url] = client_id
        self._task_to_session[client_id] = client_id

        return self._make_result(client_id, session)

    async def stop(self, task_id: str) -> bool:
        """Остановка проксирования.
        
        ВАЖНО: НЕ удаляет временные файлы — это задача модуля Stream.
        """
        # Убираем маппинг клиента
        master_id = self._task_to_session.pop(task_id, None)
        if not master_id:
            return False
            
        if task_id == master_id:
            session = self._sessions.pop(master_id, None)
            if session:
                url = session.task.input_url
                if self._url_to_session.get(url) == master_id:
                    self._url_to_session.pop(url, None)
                session.stop()
                return True
        return True

    # ── Вспомогательные ─────────────────────────────────────────────────

    def _make_result(
        self, task_id: str, session: ProxySession
    ) -> StreamResult:
        """Формирование результата запуска."""
        output_url = f"/api/modules/stream/v1/proxy/{task_id}"
        if session.task.output_type == OutputType.HLS:
            output_url = f"{output_url}/index.m3u8"

        return StreamResult(
            task_id=task_id,
            success=True,
            backend_used="builtin_proxy",
            output_url=output_url,
            metadata={
                "type": "buffered_proxy",
                "buffer_dir": session.buffer_dir,
                "protocol": session.task.input_protocol.value,
                "segments_count": len(session.segments)
            }
        )

    # ── Публичный контракт ──────────────────────────────────────────────

    def get_session(self, task_id: str) -> Optional[ProxySession]:
        """Получить активную ProxySession по ID."""
        master_id = self._task_to_session.get(task_id)
        if master_id:
            return self._sessions.get(master_id)
        return None

    def get_active_count(self) -> int:
        """Количество активных сессий прокси."""
        return len(self._sessions)
