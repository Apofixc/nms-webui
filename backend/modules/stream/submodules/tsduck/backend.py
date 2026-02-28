# Логика трансляции через TSDuck (tsp)
import asyncio
import logging
import signal
import uuid
from typing import Dict, List, Optional

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

logger = logging.getLogger(__name__)


class TSDuckStreamer:
    """Управление процессами TSDuck (tsp)."""

    def __init__(self, binary_path: str = "tsp"):
        self.binary_path = binary_path
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]
        
        try:
            cmd = self._build_command(task)
            logger.info(f"TSDuck Stream [{task_id}]: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            await asyncio.sleep(1.5)
            if process.returncode is not None:
                stderr = await process.stderr.read()
                return StreamResult(
                    task_id=task_id, success=False, backend_used="tsduck",
                    error=f"TSDuck завершился: {stderr.decode(errors='replace')[-500:]}"
                )

            return StreamResult(
                task_id=task_id, success=True, backend_used="tsduck",
                output_url=f"/api/v1/m/stream/play/{task_id}",
                metadata={"pid": process.pid, "args": cmd}
            )

        except Exception as e:
            logger.error(f"Ошибка TSDuck [{task_id}]: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id, success=False, backend_used="tsduck", error=str(e)
            )

    async def stop(self, task_id: str) -> bool:
        process = self._processes.pop(task_id, None)
        if process:
            if process.returncode is None:
                try:
                    process.send_signal(signal.SIGTERM)
                    await asyncio.wait_for(process.wait(), timeout=5)
                except (asyncio.TimeoutError, ProcessLookupError):
                    process.kill()
                    await process.wait()
        return process is not None

    def _build_command(self, task: StreamTask) -> List[str]:
        """Построение команды tsp."""
        cmd = [self.binary_path]
        
        # Вход (Input Plugins)
        if task.input_protocol == StreamProtocol.UDP:
            addr = task.input_url.replace("udp://", "").replace("@", "")
            cmd.extend(["-I", "ip", addr])
        elif task.input_protocol == StreamProtocol.SRT:
            addr = task.input_url.replace("srt://", "")
            cmd.extend(["-I", "srt", "--caller", addr])
        elif task.input_protocol == StreamProtocol.HTTP:
            cmd.extend(["-I", "http", task.input_url])
        else:
            cmd.extend(["-I", "http", task.input_url])

        # Обработка (Packet Plugins)
        # Добавляем плагин мониторинга или коррекции PCR/PTS если нужно
        cmd.extend(["-P", "continuity"])

        # Выход (Output Plugins)
        if task.output_type == OutputType.UDP:
            # cmd.extend(["-O", "ip", "239.1.1.1:1234"])
            cmd.extend(["-O", "file", "/dev/stdout"]) # Проброс через stdout
        else:
            cmd.extend(["-O", "file", "/dev/stdout"])

        return cmd

    def get_active_count(self) -> int:
        return len(self._processes)
