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

logger = logging.getLogger(__name__)


class AstraStreamer:
    """Управление процессами Astra.

    Генерирует Lua-скрипты для make_channel с параметрами из настроек.
    Поддерживает override — полная замена Lua-скрипта шаблоном.
    """

    def __init__(self, settings: dict):
        self.binary_path = settings.get("binary_path", "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182")
        self.http_port = settings.get("http_port", 8100)

        # -- HTTP (Input) --
        self.ua = settings.get("ua", "Astra")
        self.http_input_timeout = settings.get("http_input_timeout", 10)
        self.http_input_buffer_size = settings.get("http_input_buffer_size", 1024)

        # -- HTTP (Output) --
        self.http_buffer_size = settings.get("http_buffer_size", 1024)
        self.http_buffer_fill = settings.get("http_buffer_fill", 256)

        # -- UDP (Output) --
        self.udp_ttl = settings.get("udp_ttl", 32)

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

        # -- Дешифрование --
        self.biss_key = settings.get("biss_key", "")

        # -- Override --
        self.override_lua = settings.get("override_lua", "")

        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._temp_files: Dict[str, str] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            # Форматирование адресов для Astra
            input_addr = self._format_input_addr(task.input_url, task.input_protocol)
            output_addr = self._format_output_addr(task_id)

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
            logger.info(f"Astra Stream [{task_id}]: {self.binary_path} {path}")
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

            return StreamResult(
                task_id=task_id, success=True, backend_used="astra",
                output_url=f"http://127.0.0.1:{self.http_port}/{task_id}",
                metadata={"pid": process.pid, "lua": path}
            )

        except Exception as e:
            logger.error(f"Ошибка Astra [{task_id}]: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id, success=False, backend_used="astra", error=str(e)
            )

    async def stop(self, task_id: str) -> bool:
        process = self._processes.pop(task_id, None)
        lua_path = self._temp_files.pop(task_id, None)

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

    def _from_override(self, input_addr: str, output_addr: str, task_id: str) -> str:
        """Подстановка переменных в override Lua-шаблон."""
        try:
            return self.override_lua.format(
                input_url=input_addr,
                output_url=output_addr,
                task_id=task_id,
                http_port=self.http_port,
            )
        except (KeyError, ValueError) as e:
            logger.warning(f"Ошибка в override Lua-шаблоне: {e}. Используется штатная генерация.")
            return self._build_lua(input_addr, output_addr, task_id)

    # ── Форматирование адресов ───────────────────────────────────

    def _format_input_addr(self, url: str, protocol: StreamProtocol) -> str:
        """Форматирование входного URL под синтаксис Astra (module://addr#params)."""
        options = []

        # Общие параметры входа
        if self.ua:
            options.append(f"ua={self.ua}")
        if self.http_input_timeout and protocol == StreamProtocol.HTTP:
            options.append(f"timeout={self.http_input_timeout}")
        if self.http_input_buffer_size and protocol == StreamProtocol.HTTP:
            options.append(f"buffer_size={self.http_input_buffer_size}")

        # Фильтрация/дешифрование
        if self.pid_filter:
            options.append(f"filter={self.pid_filter}")
        if self.biss_key:
            options.append(f"biss={self.biss_key}")

        opt_str = "&".join(options)
        suffix = f"#{opt_str}" if opt_str else ""
        return url + suffix

    def _format_output_addr(self, task_id: str) -> str:
        """Форматирование выходного HTTP-адреса с параметрами буфера."""
        options = []
        if self.http_buffer_size != 1024:
            options.append(f"buffer_size={self.http_buffer_size}")
        if self.http_buffer_fill != 256:
            options.append(f"buffer_fill={self.http_buffer_fill}")

        opt_str = "&".join(options)
        suffix = f"#{opt_str}" if opt_str else ""
        return f"http://0.0.0.0:{self.http_port}/{task_id}{suffix}"

    def get_active_count(self) -> int:
        return len(self._processes)
