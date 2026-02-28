# Субмодуль TSDuck — стриминг по сетевым протоколам (IP/TS)
# Использует tsp (Transport Stream Processor) для обработки потоков
import asyncio
import logging
import os
import shutil
import signal
import uuid
from typing import Dict, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

logger = logging.getLogger(__name__)


class TSDuckBackend(IStreamBackend):
    """Бэкенд на основе TSDuck (tsp).

    Специализация: обработка Transport Stream через цепочки плагинов.
    Типичная команда: tsp -I ip <source> -P <plugins...> -O ip <dest>
    """

    def __init__(self, tsp_path: str = "tsp", timeout: int = 30) -> None:
        self._tsp_path = tsp_path
        self._timeout = timeout
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    @property
    def backend_id(self) -> str:
        return "tsduck"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.UDP, StreamProtocol.RTP, StreamProtocol.HTTP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск стриминга через tsp."""
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            cmd = self._build_command(task)
            logger.info(f"TSDuck [{task_id}]: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            await asyncio.sleep(2)

            if process.returncode is not None:
                stderr = await process.stderr.read()
                error_msg = stderr.decode(errors="replace")[-500:]
                return StreamResult(
                    task_id=task_id,
                    success=False,
                    backend_used="tsduck",
                    error=f"TSDuck завершился: {error_msg}",
                )

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="tsduck",
                output_url=f"/api/v1/m/stream/play/{task_id}",
                metadata={"pid": process.pid, "cmd": " ".join(cmd)},
            )

        except Exception as e:
            logger.error(f"TSDuck [{task_id}] ошибка: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id,
                success=False,
                backend_used="tsduck",
                error=str(e),
            )

    async def stop_stream(self, task_id: str) -> bool:
        """Остановка TSDuck процесса."""
        process = self._processes.pop(task_id, None)
        if not process:
            return False
        if process.returncode is None:
            try:
                process.send_signal(signal.SIGTERM)
                await asyncio.wait_for(process.wait(), timeout=5)
            except (asyncio.TimeoutError, ProcessLookupError):
                process.kill()
                await process.wait()
        return True

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return None

    async def is_available(self) -> bool:
        """Проверка наличия tsp."""
        if shutil.which(self._tsp_path):
            return True
        return os.path.isfile(self._tsp_path) and os.access(self._tsp_path, os.X_OK)

    async def health_check(self) -> dict:
        available = await self.is_available()
        result = {"backend": "tsduck", "path": self._tsp_path, "available": available}
        if available:
            try:
                proc = await asyncio.create_subprocess_exec(
                    self._tsp_path, "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
                output = (stdout or stderr).decode(errors="replace").strip()
                result["version"] = output.split("\n")[0]
            except Exception:
                pass
        return result

    def _build_command(self, task: StreamTask) -> list[str]:
        """Построение команды tsp."""
        cmd = [self._tsp_path]

        # Вход
        if task.input_protocol == StreamProtocol.UDP:
            # tsp -I ip <multicast>:<port>
            addr = task.input_url.replace("udp://", "").replace("@", "")
            cmd.extend(["-I", "ip", addr])
        elif task.input_protocol == StreamProtocol.HTTP:
            cmd.extend(["-I", "http", task.input_url])
        elif task.input_protocol == StreamProtocol.RTP:
            addr = task.input_url.replace("rtp://", "")
            cmd.extend(["-I", "ip", addr])
        else:
            cmd.extend(["-I", "http", task.input_url])

        # Плагины обработки (пока без фильтрации)
        cmd.extend(["-P", "continuity"])

        # Выход в stdout (для проксирования через worker_pool)
        cmd.extend(["-O", "file", "/dev/stdout"])

        return cmd


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда TSDuck."""
    path = settings.get("tsduck_path", "tsp")
    timeout = settings.get("worker_timeout", 30)
    return TSDuckBackend(tsp_path=path, timeout=timeout)
