import asyncio
import logging
import os
import socket
import tempfile
import time
import aiohttp
from typing import Dict, Optional, Any, List

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
)

logger = logging.getLogger(__name__)

class AstraSession:
    """Сессия для управления потоком Astra."""
    def __init__(self, task_id: str, task: StreamTask):
        self.task_id = task_id
        self.task = task
        self._subscribers: List[asyncio.Queue] = []
        self.script_path: Optional[str] = None

    def subscribe(self) -> asyncio.Queue:
        # Увеличиваем очередь для компенсации сетевого джиттера
        queue = asyncio.Queue(maxsize=512)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def dispatch(self, chunk: bytes):
        for q in self._subscribers:
            try:
                if q.full(): q.get_nowait()
                q.put_nowait(chunk)
            except: pass

    async def cleanup(self):
        if self.script_path and os.path.exists(self.script_path):
            try: os.remove(self.script_path)
            except: pass

class AstraStreamer:
    """Управление Cesbo Astra."""

    def __init__(self, settings: dict):
        self._settings = settings
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._local_urls: Dict[str, str] = {}
        self._astra_urls: Dict[str, str] = {}
        self._bridge_tasks: Dict[str, asyncio.Task] = {}
        self._sessions: Dict[str, AstraSession] = {}

    def _get_setting(self, key: str, default: Any) -> Any:
        return self._settings.get(key, default)

    def _get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or f"astra_{int(time.time())}"
        astra_path = self._get_setting("binary_path", "astra")
        
        # 1. Формирование входного URL
        input_url = task.input_url
        try:
            # Магия UDP: если это мультикаст, Astra 4.4 обычно требует @ для Join Group
            if input_url.startswith("udp://"):
                from urllib.parse import urlparse
                p = urlparse(input_url)
                if p.hostname:
                    first_octet = int(p.hostname.split('.')[0]) if p.hostname.split('.')[0].isdigit() else 0
                    if 224 <= first_octet <= 239 and "@" not in input_url:
                        input_url = input_url.replace("udp://", "udp://@")
        except:
            pass
            
        # 2. Формирование Lua скрипта
        port = self._get_free_port()
        stream_path = f"stream_{task_id}"
        astra_url = f"http://127.0.0.1:{port}/{stream_path}"
        
        # Пытаемся определить путь к библиотекам
        lib_path = "/opt/Cesbo-Astra-4.4.-monitor/lib-monitor/?.lua"
        if os.path.isabs(astra_path):
            base_dir = os.path.dirname(astra_path)
            potential_lib_dir = os.path.join(base_dir, "lib-monitor")
            if os.path.exists(potential_lib_dir):
                lib_path = os.path.join(potential_lib_dir, "?.lua")
        
        lua_script = f"""
package.path = "{lib_path};;" .. package.path

make_channel({{
    name = "{task_id}",
    input = {{ "{input_url}" }},
    output = {{ "http://0:{port}/{stream_path}" }}
}})
"""
        # Создаем временный файл
        fd, script_path = tempfile.mkstemp(suffix=".lua", prefix="astra_")
        with os.fdopen(fd, 'w') as f:
            f.write(lua_script)
            
        session = AstraSession(task_id, task)
        session.script_path = script_path
        self._sessions[task_id] = session
        
        # 3. Запуск процесса
        cmd = f"{astra_path} {script_path}"
        
        try:
            logger.info(f"Astra Start: {cmd}")
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._processes[task_id] = process
            
            # 4. Ожидание запуска порта
            success = False
            for _ in range(20):
                await asyncio.sleep(0.5)
                if process.returncode is not None: break
                try:
                    r, w = await asyncio.open_connection('127.0.0.1', port)
                    w.close()
                    await w.wait_closed()
                    success = True
                    break
                except: continue
                
            if not success:
                error_msg = "Astra port timeout"
                await self.stop(task_id)
                return StreamResult(task_id=task_id, success=False, backend_used="astra", error=error_msg)

            # 5. Настройка моста
            local_url = f"/api/modules/stream/v1/proxy/{task_id}"
            self._bridge_tasks[task_id] = asyncio.create_task(
                self._astra_bridge(task_id, astra_url, session)
            )

            return StreamResult(
                task_id=task_id, 
                success=True, 
                backend_used="astra",
                output_type=OutputType.HTTP, 
                output_url=local_url, 
                process=process
            )
            
        except Exception as e:
            logger.exception("Failed to start Astra")
            return StreamResult(task_id=task_id, success=False, backend_used="astra", error=str(e))

    async def _astra_bridge(self, task_id: str, url: str, session: AstraSession):
        """Проксирование потока из Astra в очереди подписчиков."""
        max_attempts = 20
        for attempt in range(max_attempts):
            try:
                await asyncio.sleep(0.5)
                connector = aiohttp.TCPConnector(force_close=True)
                # Astra может долго инициализировать входящий UDP поток
                timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=60)
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as http_session:
                    async with http_session.get(url) as response:
                        if response.status == 200:
                            logger.info(f"Astra Bridge [{task_id}]: connected")
                            
                            synced = False
                            bridge_buffer = bytearray()
                            
                            async for chunk, _ in response.content.iter_chunks():
                                if not synced:
                                    idx = chunk.find(b'\x47')
                                    if idx != -1:
                                        chunk = chunk[idx:]
                                        synced = True
                                    else:
                                        continue
                                
                                bridge_buffer.extend(chunk)
                                
                                # Накапливаем блок (16КБ) для снижения нагрузки на event loop
                                if len(bridge_buffer) >= 16384:
                                    session.dispatch(bytes(bridge_buffer))
                                    bridge_buffer.clear()
                            
                            # Отправляем остаток
                            if bridge_buffer:
                                session.dispatch(bytes(bridge_buffer))
                            return
                        else:
                            logger.warning(f"Astra Bridge [{task_id}]: HTTP {response.status}")
            except asyncio.CancelledError: 
                break
            except Exception as e:
                if attempt % 5 == 0:
                    logger.debug(f"Astra Bridge [{task_id}] attempt {attempt} failed: {e}")
            await asyncio.sleep(1.0)

    async def stop(self, task_id: str) -> bool:
        process = self._processes.pop(task_id, None)
        self._local_urls.pop(task_id, None)
        self._astra_urls.pop(task_id, None)
        
        bridge_task = self._bridge_tasks.pop(task_id, None)
        if bridge_task: 
            bridge_task.cancel()
            
        session = self._sessions.pop(task_id, None)
        if session: 
            await session.cleanup()
            
        if process:
            try: 
                process.kill()
                await process.wait()
            except: 
                pass
        return True

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        session = self._sessions.get(task_id)
        if not session: return None
        
        # Astra в данной реализации всегда отдает HTTP поток (MPEG-TS)
        q = session.subscribe()
        return {
            "type": "proxy_queue", 
            "content_type": "video/mp2t", 
            "queue": q, 
            "unsubscribe": lambda: session.unsubscribe(q)
        }

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        return self._processes.get(task_id)

    def get_active_count(self) -> int:
        return len(self._processes)
