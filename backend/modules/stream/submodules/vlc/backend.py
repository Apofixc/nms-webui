# Логика трансляции через VLC (cvlc)
import asyncio
import logging
import signal
import uuid
from typing import Dict, List, Optional

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

logger = logging.getLogger(__name__)


class VLCStreamer:
    """Управление процессами VLC."""

    def __init__(self, binary_path: str = "cvlc"):
        self.binary_path = binary_path
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]
        
        try:
            cmd = self._build_command(task, task_id)
            logger.info(f"VLC Stream [{task_id}]: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            await asyncio.sleep(2)
            if process.returncode is not None:
                stderr = await process.stderr.read()
                return StreamResult(
                    task_id=task_id, success=False, backend_used="vlc",
                    error=f"VLC завершился: {stderr.decode(errors='replace')[-500:]}"
                )

            return StreamResult(
                task_id=task_id, success=True, backend_used="vlc",
                output_url=f"/api/v1/m/stream/play/{task_id}",
                metadata={"pid": process.pid}
            )

        except Exception as e:
            logger.error(f"Ошибка VLC [{task_id}]: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id, success=False, backend_used="vlc", error=str(e)
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

    def _build_command(self, task: StreamTask, task_id: str) -> List[str]:
        """Построение команды cvlc."""
        # --no-video-title-show --no-stats --no-audio
        cmd = [self.binary_path, task.input_url, "--no-audio", "--sout-keep"]
        
        # Вывод
        if task.output_type == OutputType.HTTP:
            cmd.append("--sout=#std{access=http,mux=ts,dst=:8080/" + task_id + "}")
        elif task.output_type == OutputType.UDP:
            cmd.append("--sout=#std{access=udp,mux=ts,dst=127.0.0.1:1234}")
        else:
            # По умолчанию: сброс в файл/stdout (менее эффективно для VLC)
            cmd.append("--sout=#std{access=file,mux=ts,dst=-}")

        return cmd

    def get_active_count(self) -> int:
        return len(self._processes)
