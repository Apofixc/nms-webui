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

# Шаблон Lua-конфигурации для Astra
LUA_TEMPLATE = """
log.set({{ color = true }})

make_channel({{
    name = "{name}",
    input = {{ "{input_url}" }},
    output = {{ "{output_url}" }},
    http_keep_active = {keep_active},
    {extra_options}
}})
"""


class AstraStreamer:
    """Управление процессами Astra."""

    def __init__(self, binary_path: str, http_port: int, settings: dict):
        self.binary_path = binary_path
        self.http_port = http_port
        self.settings = settings
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._temp_files: Dict[str, str] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]
        
        try:
            # Форматирование адресов для Astra
            input_addr = self._format_addr(task.input_url, task.input_protocol)
            output_addr = f"http://0.0.0.0:{self.http_port}/{task_id}"

            # Генерация Lua-скрипта
            lua_content = LUA_TEMPLATE.format(
                name=task_id,
                input_url=input_addr,
                output_url=output_addr,
                keep_active=30,  # Остановка через 30 сек после отключения последнего клиента
                extra_options=self._build_extra_options()
            )

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

    def _format_addr(self, url: str, protocol: StreamProtocol) -> str:
        """Форматирование URL под синтаксис Astra (module://addr#params)."""
        options = []
        if self.settings.get("ua"): options.append(f"ua={self.settings['ua']}")
        if self.settings.get("timeout"): options.append(f"timeout={self.settings['timeout']}")
        
        opt_str = "&".join(options)
        suffix = f"#{opt_str}" if opt_str else ""
        
        if protocol == StreamProtocol.UDP:
            return url.replace("udp://", "udp://") + suffix
        elif protocol == StreamProtocol.HTTP:
            return url + suffix
        return url + suffix

    def _build_extra_options(self) -> str:
        """Дополнительные параметры маппинга или дешифрования."""
        # Можно расширить для Cam-модулей, PNR и т.д.
        return ""

    def get_active_count(self) -> int:
        return len(self._processes)
