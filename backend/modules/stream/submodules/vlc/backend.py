# Логика трансляции через VLC (cvlc)
import asyncio
import logging
import os
import signal
import uuid
from typing import Dict, List, Optional

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

logger = logging.getLogger(__name__)


class VLCStreamer:
    """Управление процессами VLC.

    Поддерживает сборку --sout из параметров и override-шаблон.
    """

    def __init__(self, settings: dict):
        self.binary_path = settings.get("binary_path", "cvlc")

        # -- HTTP_TS --
        self.http_port = settings.get("http_port", 8080)
        self.http_mux = settings.get("http_mux", "ts")

        # -- HLS --
        self.hls_seglen = settings.get("hls_seglen", 5)
        self.hls_numsegs = settings.get("hls_numsegs", 5)

        # -- Override --
        self.override_http_ts = settings.get("override_http_ts", "")
        self.override_hls = settings.get("override_hls", "")

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
                output_url=f"/api/modules/stream/v1/play/{task_id}",
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

    # ── Сборка команд ─────────────────────────────────────────────

    def _build_command(self, task: StreamTask, task_id: str) -> List[str]:
        """Построение команды cvlc."""
        cmd = [self.binary_path, task.input_url, "--no-audio", "--sout-keep"]
        hls_dir = f"/tmp/stream_hls_{task_id}"

        if task.output_type == OutputType.HLS:
            sout = self._sout_hls(task_id, hls_dir)
        else:
            sout = self._sout_http_ts(task_id)

        cmd.append(sout)
        return cmd

    def _sout_http_ts(self, task_id: str) -> str:
        """--sout для HTTP_TS."""
        if self.override_http_ts:
            try:
                return self.override_http_ts.format(
                    task_id=task_id,
                    http_port=self.http_port
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"VLC override HTTP_TS ошибка: {e}")

        return f"--sout=#std{{access=http,mux={self.http_mux},dst=:{self.http_port}/{task_id}}}"

    def _sout_hls(self, task_id: str, hls_dir: str) -> str:
        """--sout для HLS."""
        os.makedirs(hls_dir, exist_ok=True)

        if self.override_hls:
            try:
                return self.override_hls.format(
                    task_id=task_id,
                    hls_dir=hls_dir
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"VLC override HLS ошибка: {e}")

        return (
            f"--sout=#livehttp{{"
            f"seglen={self.hls_seglen},"
            f"numsegs={self.hls_numsegs},"
            f"index={hls_dir}/playlist.m3u8,"
            f"index-url=/hls/{task_id}/########.ts,"
            f"dst={hls_dir}/########.ts"
            f"}}"
        )

    def get_active_count(self) -> int:
        return len(self._processes)
