# Логика трансляции через GStreamer (gst-launch-1.0)
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


class GStreamerStreamer:
    """Управление процессами GStreamer.

    Поддерживает два режима:
    1. Автоматическая сборка пайплайна из базовых параметров.
    2. Override-шаблон: если задан override_{pipeline}.
    """

    def __init__(self, settings: dict):
        self.binary_path = settings.get("binary_path", "gst-launch-1.0")

        # -- Сеть (Input) --
        self.udp_default_port = settings.get("udp_default_port", 5000)
        self.udp_caps = settings.get("udp_caps", "application/x-rtp,media=video,clock-rate=90000,encoding-name=H264")

        # -- HTTP_TS --
        self.http_ts_muxer = settings.get("http_ts_muxer", "mpegtsmux")

        # -- HLS Pipeline --
        self.hls_target_duration = settings.get("hls_target_duration", 5)
        self.hls_max_files = settings.get("hls_max_files", 5)
        self.hls_encoder = settings.get("hls_encoder", "x264enc")
        self.hls_encoder_args = settings.get("hls_encoder_args", "tune=zerolatency speed-preset=superfast")

        # -- WebRTC Pipeline --
        self.stun_server = settings.get("stun_server")
        self.webrtc_video_bitrate = settings.get("webrtc_video_bitrate", 2000)
        self.webrtc_audio_encoder = settings.get("webrtc_audio_encoder", "opusenc")

        # -- Override-шаблоны --
        self.override_http_ts = settings.get("override_http_ts", "")
        self.override_hls = settings.get("override_hls", "")
        self.override_webrtc = settings.get("override_webrtc", "")

        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            pipeline = self._build_pipeline(task, task_id)
            cmd = [self.binary_path, "-e"] + shlex.split(pipeline)

            logger.info(f"GStreamer Stream [{task_id}]: {pipeline}")
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
                    task_id=task_id, success=False, backend_used="gstreamer",
                    error=f"GStreamer завершился: {stderr.decode(errors='replace')[-500:]}"
                )

            return StreamResult(
                task_id=task_id, success=True, backend_used="gstreamer",
                output_url=f"/api/v1/m/stream/play/{task_id}",
                metadata={"pid": process.pid, "pipeline": pipeline}
            )

        except Exception as e:
            logger.error(f"Ошибка GStreamer [{task_id}]: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id, success=False, backend_used="gstreamer", error=str(e)
            )

    async def stop(self, task_id: str) -> bool:
        process = self._processes.pop(task_id, None)
        if process:
            if process.returncode is None:
                try:
                    process.send_signal(signal.SIGINT)
                    await asyncio.wait_for(process.wait(), timeout=5)
                except (asyncio.TimeoutError, ProcessLookupError):
                    process.kill()
                    await process.wait()
        return process is not None

    # ── Сборка пайплайнов ────────────────────────────────────────

    def _build_pipeline(self, task: StreamTask, task_id: str) -> str:
        """Построение GStreamer пайплайна.

        Если задан override — используется он, иначе сборка из параметров.
        """
        src = self._source_element(task.input_url, task.input_protocol)
        hls_dir = f"/tmp/stream_hls_{task_id}"

        if task.output_type == OutputType.HLS:
            override = self._apply_override(self.override_hls, src, task_id, hls_dir=hls_dir)
            if override:
                return override
            return self._pipeline_hls(src, task_id, hls_dir)

        elif task.output_type == OutputType.WEBRTC:
            override = self._apply_override(self.override_webrtc, src, task_id)
            if override:
                return override
            return self._pipeline_webrtc(src)

        else:
            # HTTP / HTTP_TS
            override = self._apply_override(self.override_http_ts, src, task_id)
            if override:
                return override
            return self._pipeline_http_ts(src)

    def _pipeline_hls(self, src: str, task_id: str, hls_dir: str) -> str:
        """Пайплайн: Input -> HLS (M3U8 + TS сегменты)."""
        os.makedirs(hls_dir, exist_ok=True)

        encoder = f"{self.hls_encoder} {self.hls_encoder_args}" if self.hls_encoder_args else self.hls_encoder

        return (
            f"{src} ! decodebin ! videoconvert ! {encoder} ! mpegtsmux ! "
            f"hlssink playlist-root=/hls/{task_id} "
            f"location={hls_dir}/segment%05d.ts playlist-location={hls_dir}/playlist.m3u8 "
            f"target-duration={self.hls_target_duration} max-files={self.hls_max_files}"
        )

    def _pipeline_webrtc(self, src: str) -> str:
        """Пайплайн: Input -> WebRTC (webrtcbin)."""
        return (
            f"{src} ! decodebin name=dbin "
            f"dbin. ! queue ! videoconvert ! x264enc bitrate={self.webrtc_video_bitrate} tune=zerolatency ! "
            f"rtph264pay config-interval=1 ! application/x-rtp,media=video,encoding-name=H264,payload=96 ! webrtcbin name=s "
            f"dbin. ! queue ! audioconvert ! {self.webrtc_audio_encoder} ! "
            f"rtpopuspay ! application/x-rtp,media=audio,encoding-name=OPUS,payload=97 ! s."
        )

    def _pipeline_http_ts(self, src: str) -> str:
        """Пайплайн: Input -> MPEG-TS в stdout."""
        return f"{src} ! decodebin ! {self.http_ts_muxer} ! fdsink fd=1"

    # ── Source element ────────────────────────────────────────────

    def _source_element(self, url: str, protocol: StreamProtocol) -> str:
        """Формирование элемента-источника GStreamer."""
        if protocol == StreamProtocol.UDP:
            addr = url.replace("udp://", "").replace("@", "")
            host, port = addr.split(":") if ":" in addr else (addr, str(self.udp_default_port))
            return f'udpsrc address={host} port={port} caps="{self.udp_caps}"'
        elif protocol == StreamProtocol.RTSP:
            return f"rtspsrc location={url} ! rtpjitterbuffer"
        elif protocol == StreamProtocol.RTP:
            addr = url.replace("rtp://", "")
            host, port = addr.split(":") if ":" in addr else (addr, "5004")
            return f'udpsrc address={host} port={port} caps="application/x-rtp"'
        elif protocol == StreamProtocol.SRT:
            return f'srtsrc uri="{url}"'
        else:
            return f"souphttpsrc location={url}"

    # ── Override ──────────────────────────────────────────────────

    def _apply_override(self, template: str, source: str, task_id: str, hls_dir: str = "") -> Optional[str]:
        """Подстановка переменных в override-шаблон."""
        if not template:
            return None
        try:
            return template.format(
                source=source,
                task_id=task_id,
                hls_dir=hls_dir,
            )
        except (KeyError, ValueError) as e:
            logger.warning(f"Ошибка в override-шаблоне GStreamer: {e}. Используется штатная логика.")
            return None

    def get_active_count(self) -> int:
        return len(self._processes)
