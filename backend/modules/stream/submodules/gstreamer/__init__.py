# Субмодуль GStreamer — высокопроизводительная конвертация и превью
# Использует gst-launch-1.0 для построения пайплайнов
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


class GStreamerBackend(IStreamBackend):
    """Бэкенд на основе GStreamer (gst-launch-1.0).

    Строит GStreamer пайплайны для конвертации видеопотоков
    и генерации превью через элемент pngenc/jpegenc.
    """

    def __init__(self, gst_path: str = "gst-launch-1.0", timeout: int = 30) -> None:
        self._gst_path = gst_path
        self._timeout = timeout
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    @property
    def backend_id(self) -> str:
        return "gstreamer"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.CONVERSION, BackendCapability.PREVIEW}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.UDP,
            StreamProtocol.RTP, StreamProtocol.RTSP,
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {PreviewFormat.JPEG, PreviewFormat.PNG, PreviewFormat.WEBP}

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск стриминга через GStreamer pipeline."""
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            pipeline_str = self._build_stream_pipeline(task)
            cmd = [self._gst_path, "-e", pipeline_str]
            logger.info(f"GStreamer [{task_id}]: {' '.join(cmd)}")

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
                    task_id=task_id,
                    success=False,
                    backend_used="gstreamer",
                    error=stderr.decode(errors="replace")[-500:],
                )

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="gstreamer",
                output_url=f"/api/v1/m/stream/play/{task_id}",
                metadata={"pid": process.pid},
            )

        except Exception as e:
            logger.error(f"GStreamer [{task_id}] ошибка: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id, success=False,
                backend_used="gstreamer", error=str(e),
            )

    async def stop_stream(self, task_id: str) -> bool:
        """Остановка GStreamer pipeline."""
        process = self._processes.pop(task_id, None)
        if not process:
            return False
        if process.returncode is None:
            try:
                process.send_signal(signal.SIGINT)  # GStreamer реагирует на SIGINT
                await asyncio.wait_for(process.wait(), timeout=5)
            except (asyncio.TimeoutError, ProcessLookupError):
                process.kill()
                await process.wait()
        return True

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        """Генерация превью через GStreamer pipeline.

        Строит pipeline: source ! decodebin ! videoscale ! videoconvert ! encoder ! fdsink
        """
        pipeline_str = self._build_preview_pipeline(url, protocol, fmt, width, quality)
        cmd = [self._gst_path, "-e", pipeline_str]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._timeout,
            )

            if process.returncode != 0:
                logger.warning(f"GStreamer превью ошибка: {stderr.decode(errors='replace')[-300:]}")
                return None

            return stdout if stdout else None

        except asyncio.TimeoutError:
            if process.returncode is None:
                process.kill()
            return None
        except Exception as e:
            logger.error(f"GStreamer превью ошибка: {e}")
            return None

    async def is_available(self) -> bool:
        if shutil.which(self._gst_path):
            return True
        return os.path.isfile(self._gst_path) and os.access(self._gst_path, os.X_OK)

    async def health_check(self) -> dict:
        available = await self.is_available()
        result = {"backend": "gstreamer", "path": self._gst_path, "available": available}
        if available:
            try:
                proc = await asyncio.create_subprocess_exec(
                    self._gst_path, "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                result["version"] = stdout.decode(errors="replace").split("\n")[0].strip()
            except Exception:
                pass
        return result

    # --- Построение GStreamer пайплайнов ---

    def _build_stream_pipeline(self, task: StreamTask) -> str:
        """Pipeline для стриминга."""
        src = self._source_element(task.input_url, task.input_protocol)
        return f"{src} ! decodebin ! queue ! mpegtsmux ! fdsink"

    def _build_preview_pipeline(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int, quality: int,
    ) -> str:
        """Pipeline для генерации превью."""
        src = self._source_element(url, protocol)

        # Элемент кодирования
        if fmt == PreviewFormat.JPEG:
            encoder = f"jpegenc quality={quality}"
        elif fmt == PreviewFormat.PNG:
            encoder = "pngenc"
        elif fmt == PreviewFormat.WEBP:
            encoder = f"webpenc quality={quality}"
        else:
            encoder = "jpegenc"

        return (
            f"{src} ! decodebin ! videoconvert ! videoscale ! "
            f"video/x-raw,width={width} ! {encoder} ! fdsink"
        )

    @staticmethod
    def _source_element(url: str, protocol: StreamProtocol) -> str:
        """GStreamer элемент источника по протоколу."""
        if protocol == StreamProtocol.UDP:
            addr = url.replace("udp://", "").replace("@", "")
            host, port = addr.split(":") if ":" in addr else (addr, "5500")
            return f"udpsrc address={host} port={port}"
        elif protocol == StreamProtocol.RTSP:
            return f"rtspsrc location={url} ! rtpjitterbuffer"
        elif protocol == StreamProtocol.RTP:
            addr = url.replace("rtp://", "")
            host, port = addr.split(":") if ":" in addr else (addr, "5004")
            return f"udpsrc address={host} port={port} caps=\"application/x-rtp\""
        else:
            return f"souphttpsrc location={url}"


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда GStreamer."""
    path = settings.get("gstreamer_path", "gst-launch-1.0")
    timeout = settings.get("worker_timeout", 30)
    return GStreamerBackend(gst_path=path, timeout=timeout)
