# Логика трансляции через Cesbo Astra (Lua-скрипты)
import asyncio
import logging
import os
import signal
import tempfile
import uuid
import time
import shutil
import aiohttp
from typing import Dict, Optional, List

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

logger = logging.getLogger(__name__)


class AstraSession:
    """Сессия для управления циклической нарезкой потока Astra в файлы (HTTP_TS)."""
    def __init__(self, task_id: str, task: StreamTask, buffer_dir: str = "", segment_duration: int = 5):
        self.task_id = task_id
        self.task = task
        self.buffer_dir = buffer_dir
        self.segment_duration = segment_duration
        self._segments: List[str] = []
        self._manual_file = None
        self._seg_idx = 1
        self._seg_start_time = 0
        self._max_segments = 24  # Около 2 минут буфера
        self._current_name = None

    async def write_chunk(self, chunk: bytes):
        """Запись данных в текущий сегмент с ротацией."""
        now = time.time()
        if not self._manual_file or (now - self._seg_start_time) >= self.segment_duration:
            await self._rotate_segment(now)
        
        if self._manual_file:
            try:
                await asyncio.to_thread(self._manual_file.write, chunk)
                await asyncio.to_thread(self._manual_file.flush)
            except Exception as e:
                logger.error(f"Ошибка записи сегмента Astra {self.task_id}: {e}")

    async def _rotate_segment(self, now):
        """Смена файла сегмента и удаление старых."""
        if self._manual_file:
            f = self._manual_file
            self._manual_file = None
            await asyncio.to_thread(f.close)
            if self._current_name:
                self._segments.append(self._current_name)
                while len(self._segments) > self._max_segments:
                    old = self._segments.pop(0)
                    try:
                        os.remove(os.path.join(self.buffer_dir, old))
                    except:
                        pass

        try:
            os.makedirs(self.buffer_dir, exist_ok=True)
            self._current_name = f"seg-{self._seg_idx:08d}.ts"
            self._manual_file = open(os.path.join(self.buffer_dir, self._current_name), "wb")
            self._seg_idx += 1
            self._seg_start_time = now
        except Exception as e:
            logger.error(f"Ошибка ротации сегмента Astra {self.task_id}: {e}")

    @property
    def segments(self) -> List[str]:
        return list(self._segments)

    def cleanup(self):
        """Полная очистка буфера при остановке."""
        if self._manual_file:
            try:
                self._manual_file.close()
            except:
                pass
        if os.path.exists(self.buffer_dir):
            shutil.rmtree(self.buffer_dir, ignore_errors=True)


class AstraStreamer:
    """Управление процессами Astra с поддержкой циклической сегментации."""

    def __init__(self, settings: dict):
        self.binary_path = settings.get("binary_path", "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182")
        self.http_port = settings.get("http_port", 8100)
        self.data_dir = settings.get("data_dir", "/opt/nms-webui/data/streams")

        # -- Настройки буфера трансляции --
        self.http_buffer_size = settings.get("http_buffer_size", 1024)
        self.http_buffer_fill = settings.get("http_buffer_fill", 256)
        self.udp_ttl = settings.get("udp_ttl", 32)

        # -- Параметры make_channel --
        self.http_keep_active = settings.get("http_keep_active", 30)
        self.channel_timeout = settings.get("channel_timeout", 0)
        self.no_reload = settings.get("no_reload", False)
        self.pass_sdt = settings.get("pass_sdt", False)
        self.pass_eit = settings.get("pass_eit", False)
        self.set_pnr = settings.get("set_pnr", 0)
        self.set_tsid = settings.get("set_tsid", 0)
        self.service_name = settings.get("service_name", "")
        self.service_provider = settings.get("service_provider", "")
        self.pid_map = settings.get("pid_map", "")
        self.pid_filter = settings.get("pid_filter", "")

        # -- Дешифрование --
        self.biss_key = settings.get("biss_key", "")

        # -- Override --
        self.override_lua = settings.get("override_lua", "")

        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._temp_files: Dict[str, str] = {}
        self._sessions: Dict[str, AstraSession] = {}
        self._background_tasks: Dict[str, asyncio.Task] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            # Для всех режимов Astra выдает поток по HTTP локально
            input_addr = self._format_input_addr(task.input_url, task.input_protocol)
            output_addr = self._format_astra_http_addr(task_id)

            # Генерация Lua-скрипта
            if self.override_lua:
                lua_content = self._from_override(input_addr, output_addr, task_id)
            else:
                lua_content = self._build_lua(input_addr, output_addr, task_id)

            # Сохранение во временный файл
            fd, path = tempfile.mkstemp(prefix=f"astra_{task_id}_", suffix=".lua")
            with os.fdopen(fd, 'w') as f:
                f.write(lua_content)
            self._temp_files[task_id] = path

            # Запуск Astra
            logger.info(f"Astra Start [{task_id}]: {self.binary_path} {path}")
            process = await asyncio.create_subprocess_exec(
                self.binary_path, path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            await asyncio.sleep(2)
            if process.returncode is not None:
                stderr = await process.stderr.read()
                return StreamResult(
                    task_id=task_id, success=False, backend_used="astra",
                    error=f"Astra завершилась: {stderr.decode(errors='replace')[-500:]}"
                )

            # URL для внутреннего проксирования (локальный порт Astra)
            astra_local_url = f"http://127.0.0.1:{self.http_port}/{task_id}"
            out_url = astra_local_url
            
            # Если выбран HTTP_TS — запускаем нарезку сегментов (циклический буфер)
            if task.output_type == OutputType.HTTP_TS:
                buffer_dir = os.path.join(self.data_dir, f"astra_buf_{task_id}")
                session = AstraSession(task_id, task, buffer_dir=buffer_dir)
                self._sessions[task_id] = session
                
                # Запуск фонового процесса чтения
                self._background_tasks[task_id] = asyncio.create_task(
                    self._process_buffering(task_id, astra_local_url, session)
                )
                out_url = None # api.py увидит NULL и полезет в get_playback_info

            return StreamResult(
                task_id=task_id, success=True, backend_used="astra",
                output_url=out_url,
                metadata={"pid": process.pid, "lua": path}
            )

        except Exception as e:
            logger.error(f"Ошибка Astra [{task_id}]: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id, success=False, backend_used="astra", error=str(e)
            )

    async def _process_buffering(self, task_id: str, url: str, session: AstraSession):
        """Фоновое чтение из HTTP-выхода Astra и нарезка сегментов."""
        max_retries = 10
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Ждем короткое время, пока Astra поднимет HTTP порт
                await asyncio.sleep(retry_delay)
                
                timeout = aiohttp.ClientTimeout(total=None, connect=5, sock_read=60)
                async with aiohttp.ClientSession(timeout=timeout) as http:
                    async with http.get(url) as resp:
                        if resp.status == 200:
                            logger.info(f"Astra Buffering [{task_id}] connected.")
                            async for chunk in resp.content.iter_any():
                                await session.write_chunk(chunk)
                                if task_id not in self._processes:
                                    break
                            break
                        else:
                            logger.warning(f"Astra Buffering [{task_id}] HTTP status: {resp.status}")
            except Exception as e:
                if task_id not in self._processes:
                    break
                logger.debug(f"Astra Buffering retry {attempt+1}/{max_retries} for {task_id}: {e}")
                
        logger.info(f"Astra Buffering [{task_id}] stopped.")

    async def stop(self, task_id: str) -> bool:
        # 1. Остановить фоновую задачу буферизации
        b_task = self._background_tasks.pop(task_id, None)
        if b_task:
            b_task.cancel()

        # 2. Очистить сессию и файлы
        session = self._sessions.pop(task_id, None)
        if session:
            session.cleanup()

        # 3. Остановить процесс Astra
        process = self._processes.pop(task_id, None)
        lua_path = self._temp_files.pop(task_id, None)

        if process:
            try:
                process.send_signal(signal.SIGTERM)
                await asyncio.wait_for(process.wait(), timeout=3)
            except:
                process.kill()
                await process.wait()

        if lua_path and os.path.exists(lua_path):
            try:
                os.remove(lua_path)
            except:
                pass

        return True

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Возвращает информацию о буферизированных сегментах для api.py."""
        session = self._sessions.get(task_id)
        if not session:
            return None
        
        return {
            "type": "proxy_buffer",
            "content_type": "video/mp2t",
            "buffer_dir": session.buffer_dir,
            "segments": session.segments,
            "segment_duration": session.segment_duration,
        }

    # ── Служебные методы ─────────────────────────────────────────

    def _format_astra_http_addr(self, task_id: str) -> str:
        """Внутренний HTTP адрес, на котором Astra слушает входящих зрителей."""
        return f"http://0.0.0.0:{self.http_port}/{task_id}"

    def _format_input_addr(self, url: str, protocol: StreamProtocol) -> str:
        """Форматирование сетевого входного URL (UDP/RTP) под синтаксис Astra."""
        options = []
        if self.pid_filter:
            options.append(f"filter={self.pid_filter}")
        if self.biss_key:
            options.append(f"biss={self.biss_key}")

        if not options:
            return url

        opt_str = "&".join(options)
        return f"{url}#{opt_str}" if "#" not in url else f"{url}&{opt_str}"

    def _build_lua(self, input_addr: str, output_addr: str, task_id: str) -> str:
        """Полная сборка Lua-скрипта со всеми метаданными."""
        extra = []
        if self.channel_timeout > 0:
            extra.append(f'    timeout = {self.channel_timeout},')
        if self.no_reload:
            extra.append('    no_reload = true,')
        if self.pass_sdt:
            extra.append('    pass_sdt = true,')
        if self.pass_eit:
            extra.append('    pass_eit = true,')
        if self.set_pnr > 0:
            extra.append(f'    set_pnr = {self.set_pnr},')
        if self.set_tsid > 0:
            extra.append(f'    set_tsid = {self.set_tsid},')
        if self.service_name:
            extra.append(f'    service_name = "{self.service_name}",')
        if self.service_provider:
            extra.append(f'    service_provider = "{self.service_provider}",')
        if self.pid_map:
            extra.append(f'    map = "{self.pid_map}",')

        extra_str = "\n".join(extra)

        return f"""log.set({{ color = true }})
make_channel({{
    name = "{task_id}",
    input = {{ "{input_addr}" }},
    output = {{ "{output_addr}" }},
    http_keep_active = {self.http_keep_active},
{extra_str}
}})
"""

    def _from_override(self, input_addr: str, output_addr: str, task_id: str) -> str:
        """Подстановка переменных в кастомный Lua-шаблон."""
        try:
            return self.override_lua.format(
                input_url=input_addr,
                output_url=output_addr,
                task_id=task_id,
                http_port=self.http_port,
            )
        except Exception as e:
            logger.warning(f"Ошибка в override Lua: {e}. Используется штатная генерация.")
            return self._build_lua(input_addr, output_addr, task_id)

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        return self._processes.get(task_id)

    def get_active_count(self) -> int:
        return len(self._processes)
