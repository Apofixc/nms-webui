# Субмодуль Astra 4.4.182 — профессиональное вещание и конвертация
# Управление через Lua-скрипты (make_channel) и бинарник astra
import asyncio
import logging
import os
import signal
import tempfile
import uuid
from typing import Dict, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

logger = logging.getLogger(__name__)

# Шаблон Lua-конфигурации для простого канала
LUA_CHANNEL_TEMPLATE = """-- Автоматически сгенерировано модулем stream
-- Канал: {task_id}

log.set({{ color = true }})

make_channel({{
    name = "{task_id}",
    input = {{
        "{input_url}"
    }},
    output = {{
        "{output_url}"
    }},
    {extra_options}
}})
"""

# Шаблон для relay (проксирование)
LUA_RELAY_TEMPLATE = """-- Автоматически сгенерировано модулем stream
-- Relay: {task_id}

log.set({{ color = true }})

http_relay = http_relay or {{}}

function http_relay.on_request(client, request)
    if request.path == "/{task_id}" then
        client:send(200)
        return true
    end
    return false
end

make_channel({{
    name = "{task_id}",
    input = {{
        "{input_url}"
    }},
    output = {{
        "http://127.0.0.1:{http_port}/{task_id}"
    }},
}})
"""


class AstraProcess:
    """Управление процессом Astra."""

    def __init__(self, task_id: str, lua_path: str, astra_path: str) -> None:
        self.task_id = task_id
        self.lua_path = lua_path
        self.astra_path = astra_path
        self.process: Optional[asyncio.subprocess.Process] = None

    async def start(self) -> None:
        """Запуск astra с Lua-скриптом."""
        cmd = [self.astra_path, self.lua_path]
        logger.info(f"Astra [{self.task_id}]: {' '.join(cmd)}")

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def stop(self) -> None:
        """Остановка процесса Astra."""
        if self.process and self.process.returncode is None:
            try:
                self.process.send_signal(signal.SIGTERM)
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except ProcessLookupError:
                pass

        # Очистка временного Lua-файла
        try:
            os.unlink(self.lua_path)
        except OSError:
            pass

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.returncode is None


class AstraBackend(IStreamBackend):
    """Бэкенд Cesbo Astra 4.4.182.

    Генерирует Lua-конфигурацию и запускает бинарник astra
    для вещания и конвертации MPEG-TS потоков.

    Бинарник: /opt/Cesbo-Astra-4.4.-monitor/astra4.4.182
    Не поддерживает превью.
    """

    def __init__(
        self,
        astra_path: str = "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182",
        http_port: int = 8100,
    ) -> None:
        self._astra_path = astra_path
        self._http_port = http_port
        self._processes: Dict[str, AstraProcess] = {}

    @property
    def backend_id(self) -> str:
        return "astra"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING, BackendCapability.CONVERSION}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.UDP, StreamProtocol.RTP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск стриминга через Astra.

        1. Генерация Lua-скрипта с конфигурацией канала.
        2. Запуск бинарника astra с этим скриптом.
        3. Возврат URL для доступа к выходному потоку.
        """
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            # Форматирование входного URL для Astra
            astra_input = self._format_input_url(task.input_url, task.input_protocol)

            # Форматирование выходного URL
            astra_output = self._format_output_url(task.output_type, task_id)

            # Генерация Lua-скрипта
            lua_content = LUA_CHANNEL_TEMPLATE.format(
                task_id=task_id,
                input_url=astra_input,
                output_url=astra_output,
                extra_options="",
            )

            # Запись во временный файл
            lua_path = tempfile.mktemp(
                prefix=f"astra_{task_id}_",
                suffix=".lua",
            )
            with open(lua_path, "w") as f:
                f.write(lua_content)

            # Запуск Astra
            astra_proc = AstraProcess(
                task_id=task_id,
                lua_path=lua_path,
                astra_path=self._astra_path,
            )
            await astra_proc.start()

            # Ждём инициализации
            await asyncio.sleep(2)

            if not astra_proc.is_running:
                stderr = await astra_proc.process.stderr.read()
                error_msg = stderr.decode(errors="replace")[-500:]
                await astra_proc.stop()
                return StreamResult(
                    task_id=task_id,
                    success=False,
                    backend_used="astra",
                    error=f"Astra завершилась: {error_msg}",
                )

            self._processes[task_id] = astra_proc

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="astra",
                output_url=f"http://127.0.0.1:{self._http_port}/{task_id}",
                metadata={
                    "pid": astra_proc.process.pid,
                    "lua_path": lua_path,
                },
            )

        except Exception as e:
            logger.error(f"Astra [{task_id}] ошибка: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id,
                success=False,
                backend_used="astra",
                error=str(e),
            )

    async def stop_stream(self, task_id: str) -> bool:
        """Остановка процесса Astra."""
        astra_proc = self._processes.pop(task_id, None)
        if astra_proc:
            await astra_proc.stop()
            logger.info(f"Astra [{task_id}] остановлен")
            return True
        return False

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        # Astra не поддерживает превью
        return None

    async def is_available(self) -> bool:
        """Проверка наличия бинарника Astra."""
        return os.path.isfile(self._astra_path) and os.access(self._astra_path, os.X_OK)

    async def health_check(self) -> dict:
        available = await self.is_available()
        return {
            "backend": "astra",
            "path": self._astra_path,
            "available": available,
            "active_processes": len(self._processes),
        }

    # --- Приватные методы ---

    def _format_input_url(self, url: str, protocol: StreamProtocol) -> str:
        """Форматирование входного URL в формат Astra."""
        # Astra использует свой формат для UDP: udp://239.1.1.1:5500
        if protocol == StreamProtocol.UDP:
            return url.replace("udp://", "udp://").replace("@", "")
        return url

    def _format_output_url(self, output_type: OutputType, task_id: str) -> str:
        """Форматирование выходного URL."""
        if output_type == OutputType.HTTP:
            return f"http://127.0.0.1:{self._http_port}/{task_id}"
        elif output_type == OutputType.HTTP_TS:
            return f"http://127.0.0.1:{self._http_port}/{task_id}"
        return f"http://127.0.0.1:{self._http_port}/{task_id}"


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Astra."""
    path = settings.get("astra_path", "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182")
    return AstraBackend(astra_path=path)
