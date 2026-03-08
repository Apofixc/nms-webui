# Логика трансляции через Cesbo Astra (Lua-скрипты)
import asyncio
import logging
import os
import signal
import tempfile
import uuid
from typing import Dict, Optional, List

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

import socket
import logging

logger = logging.getLogger(__name__)


def find_free_port(start_port: int, max_attempts: int = 100) -> int:
    """Поиск свободного TCP-порта в заданном диапазоне."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    raise IOError(f"Не удалось найти свободный порт в диапазоне {start_port}-{start_port + max_attempts}")


class AstraStreamer:
    """Управление процессами Astra.

    Генерирует Lua-скрипты для make_channel с параметрами из настроек.
    Поддерживает override — полная замена Lua-скрипта шаблоном.
    """

    def __init__(self, settings: dict):
        self.binary_path = settings.get("binary_path", "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182")
        self.http_port = settings.get("http_port", 8200)

        # -- HTTP (Input) --
        self.ua = settings.get("ua", "Astra")
        self.http_input_timeout = settings.get("http_input_timeout", 10)
        self.http_input_buffer_size = settings.get("http_input_buffer_size", 1024)

        # -- HTTP (Output) --
        self.http_buffer_size = settings.get("http_buffer_size", 1024)
        self.http_buffer_fill = settings.get("http_buffer_fill", 256)

        # -- Канал (make_channel) --
        self.http_keep_active = settings.get("http_keep_active", 30)
        self.channel_timeout = settings.get("channel_timeout", 0)
        self.no_reload = settings.get("no_reload", False)
        self.pass_sdt = settings.get("pass_sdt", False)
        self.pass_eit = settings.get("pass_eit", False)

        # -- PID/PNR --
        self.set_pnr = settings.get("set_pnr", 0)
        self.set_tsid = settings.get("set_tsid", 0)
        self.service_name = settings.get("service_name", "")
        self.service_provider = settings.get("service_provider", "")
        self.pid_map = settings.get("pid_map", "")
        self.pid_filter = settings.get("pid_filter", "")

        # -- Override --
        self.override_lua = settings.get("override_lua", "")

        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._temp_files: Dict[str, str] = {}
        self._ports: Dict[str, int] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            # Поиск сводобного порта именно для этого процесса
            task_port = find_free_port(self.http_port)
            self._ports[task_id] = task_port

            # Форматирование адресов для Astra
            input_addr = self._format_input_addr(task.input_url, task.input_protocol)
            output_addr = self._format_output_addr(task_id, task_port)

            # Генерация Lua-скрипта
            if self.override_lua:
                lua_content = self._from_override(input_addr, output_addr, task_id, task_port)
            else:
                lua_content = self._build_lua(input_addr, output_addr, task_id)

            # Сохранение во временный файл
            fd, path = tempfile.mkstemp(prefix=f"astra_{task_id}_", suffix=".lua")
            with os.fdopen(fd, 'w') as f:
                f.write(lua_content)
            self._temp_files[task_id] = path

            # Запуск Astra
            logger.info(f"Astra Stream [{task_id}]: {self.binary_path} {path}")
            process = await asyncio.create_subprocess_exec(
                self.binary_path, path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            await asyncio.sleep(2)
            if process.returncode is not None:
                stdout_data, stderr_data = await process.communicate()
                error_msg = (stdout_data.decode(errors='replace') + stderr_data.decode(errors='replace'))[-1000:]
                return StreamResult(
                    task_id=task_id, success=False, backend_used="astra",
                    error=f"Astra завершилась с кодом {process.returncode}. Лог: {error_msg}"
                )

            return StreamResult(
                task_id=task_id, success=True, backend_used="astra",
                output_url=f"http://127.0.0.1:{task_port}/{task_id}",
                metadata={"pid": process.pid, "lua": path, "port": task_port}
            )

        except Exception as e:
            logger.error(f"Ошибка Astra [{task_id}]: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id, success=False, backend_used="astra", error=str(e)
            )

    async def stop(self, task_id: str) -> bool:
        process = self._processes.pop(task_id, None)
        lua_path = self._temp_files.pop(task_id, None)
        self._ports.pop(task_id, None)

        if process:
            if process.returncode is None:
                try:
                    process.send_signal(signal.SIGTERM)
                    await asyncio.wait_for(process.wait(), timeout=5)
                except (asyncio.TimeoutError, ProcessLookupError):
                    process.kill()
                    await process.wait()

        if lua_path and os.path.exists(lua_path):
            try:
                os.remove(lua_path)
            except OSError:
                pass

        return process is not None

    # ── Генерация Lua-скрипта ────────────────────────────────────

    def _build_lua(self, input_addr: str, output_addr: str, task_id: str) -> str:
        """Автоматическая генерация Lua-скрипта из настроек."""
        # Сборка дополнительных параметров make_channel
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

    def _from_override(self, input_addr: str, output_addr: str, task_id: str, port: int) -> str:
        """Подстановка переменных в override Lua-шаблон."""
        try:
            return self.override_lua.format(
                input_url=input_addr,
                output_url=output_addr,
                task_id=task_id,
                http_port=port,
            )
        except (KeyError, ValueError) as e:
            logger.warning(f"Ошибка в override Lua-шаблоне: {e}. Используется штатная генерация.")
            return self._build_lua(input_addr, output_addr, task_id)

    # ── Форматирование адресов ───────────────────────────────────

    def _format_input_addr(self, url: str, protocol: StreamProtocol) -> str:
        """Форматирование входного URL под синтаксис Astra (module://addr#params)."""
        options = []
        addr = url

        # Добавление @ для UDP и RTP (multicast syntax Astra)
        if protocol == StreamProtocol.UDP and "@" not in addr:
            addr = addr.replace("udp://", "udp://@")
        elif protocol == StreamProtocol.RTP and "@" not in addr:
            addr = addr.replace("rtp://", "rtp://@")

        # Формирование параметров (Astra 4.4 syntax)
        if protocol == StreamProtocol.HTTP:
            if self.ua:
                options.append(f"ua={self.ua}")
            if self.http_input_timeout:
                options.append(f"timeout={self.http_input_timeout}")
            if self.http_input_buffer_size:
                options.append(f"buffer_size={self.http_input_buffer_size}")
        elif protocol in {StreamProtocol.UDP, StreamProtocol.RTP}:
            # Для UDP/RTP можно передать buffer_size
            if self.http_input_buffer_size:
                options.append(f"buffer_size={self.http_input_buffer_size}")

        # Фильтрация
        if self.pid_filter:
            options.append(f"filter={self.pid_filter}")

        opt_str = "&".join(options)
        suffix = f"#{opt_str}" if opt_str else ""
        return addr + suffix

    def _format_output_addr(self, task_id: str, port: int) -> str:
        """Форматирование выходного HTTP-адреса с параметрами буфера."""
        options = []
        if self.http_buffer_size != 1024:
            options.append(f"buffer_size={self.http_buffer_size}")
        if self.http_buffer_fill != 256:
            options.append(f"buffer_fill={self.http_buffer_fill}")

        opt_str = "&".join(options)
        suffix = f"#{opt_str}" if opt_str else ""
        return f"http://0.0.0.0:{port}/{task_id}{suffix}"

    def get_task_port(self, task_id: str) -> Optional[int]:
        """Возвращает порт, выделенный для конкретной задачи."""
        return self._ports.get(task_id)

    def get_active_count(self) -> int:
        return len(self._processes)
