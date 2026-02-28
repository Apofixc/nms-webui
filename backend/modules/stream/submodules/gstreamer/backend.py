# Логика трансляции через GStreamer (gst-launch-1.0)
import asyncio
import logging
import signal
import uuid
from typing import Dict, List, Optional

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

logger = logging.getLogger(__name__)


class GStreamerStreamer:
    """Управление процессами GStreamer."""

    def __init__(self, binary_path: str = "gst-launch-1.0", stun_server: str = None):
        self.binary_path = binary_path
        self.stun_server = stun_server
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]
        
        try:
            pipeline = self._build_pipeline(task, task_id)
            cmd = [self.binary_path, "-e"] + pipeline.split()
            
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
                    # GStreamer лучше завершать через SIGINT для корректного закрытия пайплайна
                    process.send_signal(signal.SIGINT)
                    await asyncio.wait_for(process.wait(), timeout=5)
                except (asyncio.TimeoutError, ProcessLookupError):
                    process.kill()
                    await process.wait()
        return process is not None

    def _build_pipeline(self, task: StreamTask, task_id: str) -> str:
        """Построение GStreamer пайплайна."""
        src = self._source_element(task.input_url, task.input_protocol)
        
        if task.output_type == OutputType.WEBRTC:
            # Упрощенный пример для webrtcbin (требует сигнального сервера в реальности)
            return (
                f"{src} ! decodebin name=dbin "
                f"dbin. ! queue ! videoconvert ! x264enc bitrate=2000 tune=zerolatency ! rtph264pay config-interval=1 ! application/x-rtp,media=video,encoding-name=H264,payload=96 ! webrtcbin name=s "
                f"dbin. ! queue ! audioconvert ! opusenc ! rtpopuspay ! application/x-rtp,media=audio,encoding-name=OPUS,payload=97 ! s."
            )
        else:
            # Стандартный MPEG-TS вывод в stdout (pipe:1 в терминах FFmpeg)
            return f"{src} ! decodebin ! mpegtsmux ! fdsink fd=1"

    def _source_element(self, url: str, protocol: StreamProtocol) -> str:
        if protocol == StreamProtocol.UDP:
            addr = url.replace("udp://", "").replace("@", "")
            host, port = addr.split(":") if ":" in addr else (addr, "1234")
            return f"udpsrc address={host} port={port} caps=\"application/x-rtp,media=video,clock-rate=90000,encoding-name=H264\""
        elif protocol == StreamProtocol.RTSP:
            return f"rtspsrc location={url} ! rtpjitterbuffer"
        elif protocol == StreamProtocol.RTP:
            addr = url.replace("rtp://", "")
            host, port = addr.split(":") if ":" in addr else (addr, "5004")
            return f"udpsrc address={host} port={port} caps=\"application/x-rtp\""
        else:
            return f"souphttpsrc location={url}"

    def get_active_count(self) -> int:
        return len(self._processes)
