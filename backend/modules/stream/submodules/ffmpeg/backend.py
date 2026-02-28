# Логика трансляции и конвертации через FFmpeg
import asyncio
import logging
import os
import signal
import uuid
from typing import Dict, List, Optional, Set

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    BackendCapability
)

logger = logging.getLogger(__name__)


class FFmpegStreamer:
    """Управление процессами FFmpeg для стриминга."""

    def __init__(self, binary_path: str = "ffmpeg", global_args: List[str] = None):
        self.binary_path = binary_path
        self.global_args = global_args or ["-hide_banner", "-loglevel", "error"]
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]
        
        try:
            cmd = self._build_command(task, task_id)
            logger.info(f"FFmpeg Stream [{task_id}]: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[task_id] = process

            # Даем время на запуск и проверяем, не умер ли процесс сразу
            await asyncio.sleep(1.5)

            if process.returncode is not None:
                stderr = await process.stderr.read()
                error_msg = stderr.decode(errors="replace")[-500:]
                return StreamResult(
                    task_id=task_id,
                    success=False,
                    backend_used="ffmpeg",
                    error=f"FFmpeg завершился с ошибкой: {error_msg}"
                )

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="ffmpeg",
                output_url=f"/api/v1/m/stream/play/{task_id}",
                metadata={"pid": process.pid, "args": cmd}
            )

        except Exception as e:
            logger.error(f"Ошибка запуска FFmpeg [{task_id}]: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id, success=False,
                backend_used="ffmpeg", error=str(e)
            )

    async def stop(self, task_id: str) -> bool:
        process = self._processes.pop(task_id, None)
        if not process:
            return False

        if process.returncode is None:
            try:
                # Пытаемся завершить мягко (SIGTERM)
                process.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    # Если не помогло — убиваем (SIGKILL)
                    process.kill()
                    await process.wait()
            except ProcessLookupError:
                pass
        return True

    def _build_command(self, task: StreamTask, task_id: str) -> List[str]:
        """Формирование команды FFmpeg для стриминга."""
        cmd = [self.binary_path] + self.global_args

        # Входные опции в зависимости от протокола
        if task.input_protocol in (StreamProtocol.UDP, StreamProtocol.RTP):
            cmd.extend(["-thread_queue_size", "1024", "-overrun_nonfatal", "1"])
        elif task.input_protocol == StreamProtocol.RTSP:
            cmd.extend(["-rtsp_transport", "tcp"])
        
        # Вход
        cmd.extend(["-i", task.input_url])

        # Выход (копирование потока без перекодирования по умолчанию для экономии ресурсов)
        # Если нужен WebRTC или специфичный формат — тут будет логика транскодинга
        if task.output_type == OutputType.WEBRTC:
            # Для WebRTC часто нужен специфичный кодек (VP8/VP9 или H264 с профилем baseline)
            # и вывод в RTP/UDP для aiortc или другого шлюза
            cmd.extend([
                "-vcodec", "libx264", "-profile:v", "baseline", "-level", "3.0",
                "-pix_fmt", "yuv420p", "-acodec", "opus", "-f", "rtp",
                f"rtp://127.0.0.1:{10000 + hash(task_id) % 5000}"
            ])
        else:
            # По умолчанию: копирование в MPEG-TS для HTTP трансляции
            cmd.extend(["-c", "copy", "-f", "mpegts", "pipe:1"])

        return cmd

    def get_active_count(self) -> int:
        return len(self._processes)
