# Логика трансляции через TSDuck (tsp)
import asyncio
import logging
import os
import shlex
import signal
import uuid
from typing import Dict, List, Optional

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

logger = logging.getLogger(__name__)


class TSDuckStreamer:
    """Управление процессами TSDuck (tsp).

    Поддерживает сборку из параметров и override-шаблон.
    """

    def __init__(self, settings: dict):
        self.binary_path = settings.get("binary_path", "tsp")

        # -- Сеть (Input) --
        self.udp_buffer_size = settings.get("udp_buffer_size", 4096)
        self.srt_mode = settings.get("srt_mode", "caller")

        # -- HTTP_TS --
        self.continuity_check = settings.get("continuity_check", True)
        self.pcr_bitrate = settings.get("pcr_bitrate", 0)

        # -- HLS --
        self.hls_duration = settings.get("hls_duration", 5)
        self.hls_live_segments = settings.get("hls_live_segments", 5)

        # -- Обработка --
        self.extra_plugins = settings.get("extra_plugins", "")

        # -- Override --
        self.override_command = settings.get("override_command", "")

        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            cmd = self._build_command(task, task_id)
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
                output_url=f"/api/modules/stream/v1/play/{task_id}",
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

    # ── Сборка команд ─────────────────────────────────────────────

    def _build_command(self, task: StreamTask, task_id: str) -> List[str]:
        """Построение команды tsp."""
        hls_dir = f"/tmp/stream_hls_{task_id}"

        # Override
        if self.override_command:
            override = self._apply_override(task, task_id, hls_dir)
            if override:
                return override

        cmd = [self.binary_path]

        # ── Input Plugins ──
        cmd.extend(self._input_args(task))

        # ── Packet Plugins (обработка) ──
        if self.continuity_check:
            cmd.extend(["-P", "continuity"])
        if self.pcr_bitrate > 0:
            cmd.extend(["-P", "pcrbitrate", "--bitrate", str(self.pcr_bitrate)])

        # Дополнительные пользовательские плагины
        if self.extra_plugins:
            for plugin_line in self.extra_plugins.split(";"):
                plugin_line = plugin_line.strip()
                if plugin_line:
                    cmd.extend(["-P"] + plugin_line.split())

        # ── Output Plugins ──
        if task.output_type == OutputType.HLS:
            cmd.extend(self._output_hls(hls_dir))
        else:
            cmd.extend(self._output_http_ts())

        return cmd

    def _input_args(self, task: StreamTask) -> List[str]:
        """Input plugin для tsp."""
        if task.input_protocol == StreamProtocol.UDP:
            addr = task.input_url.replace("udp://", "").replace("@", "")
            args = ["-I", "ip", addr, "--buffer-size", str(self.udp_buffer_size)]
            return args
        elif task.input_protocol == StreamProtocol.SRT:
            addr = task.input_url.replace("srt://", "")
            return ["-I", "srt", f"--{self.srt_mode}", addr]
        elif task.input_protocol == StreamProtocol.HTTP:
            return ["-I", "http", task.input_url]
        else:
            return ["-I", "http", task.input_url]

    def _output_hls(self, hls_dir: str) -> List[str]:
        """Output plugin для HLS."""
        os.makedirs(hls_dir, exist_ok=True)
        return [
            "-O", "hls",
            f"{hls_dir}/playlist.m3u8",
            "--duration", str(self.hls_duration),
            "--live", str(self.hls_live_segments),
        ]

    def _output_http_ts(self) -> List[str]:
        """Output plugin для HTTP_TS (stdout)."""
        return ["-O", "file", "/dev/stdout"]

    # ── Override ──────────────────────────────────────────────────

    def _apply_override(self, task: StreamTask, task_id: str, hls_dir: str) -> Optional[List[str]]:
        """Подстановка переменных в override-шаблон."""
        try:
            rendered = self.override_command.format(
                binary_path=self.binary_path,
                input_url=task.input_url,
                task_id=task_id,
                hls_dir=hls_dir,
            )
            return shlex.split(rendered)
        except (KeyError, ValueError) as e:
            logger.warning(f"Ошибка в override-шаблоне TSDuck: {e}. Используется штатная логика.")
            return None

    def get_active_count(self) -> int:
        return len(self._processes)
