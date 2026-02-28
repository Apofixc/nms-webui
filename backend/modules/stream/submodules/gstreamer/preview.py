# Логика генерации превью через GStreamer
import asyncio
import logging
from typing import Optional, List

from backend.modules.stream.core.types import StreamProtocol, PreviewFormat

logger = logging.getLogger(__name__)


class GStreamerPreviewer:
    """Генератор превью на базе GStreamer."""

    def __init__(self, binary_path: str = "gst-launch-1.0"):
        self.binary_path = binary_path

    async def generate(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int = 640,
        quality: int = 75
    ) -> Optional[bytes]:
        
        encoder = self._get_encoder(fmt, quality)
        src = self._source_element(url, protocol)
        
        # Пайплайн для захвата одного кадра
        pipeline = (
            f"{src} ! decodebin ! timeout ! videoconvert ! videoscale ! "
            f"video/x-raw,width={width},height=-1 ! {encoder} ! fdsink fd=1"
        )
        # Примечание: 'timeout' элемент или 'num-buffers=1' в источнике (если поддерживается)
        
        cmd = [self.binary_path, "-e"] + pipeline.split()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=15
                )
            except asyncio.TimeoutError:
                if process.returncode is None:
                    process.kill()
                return None

            if process.returncode != 0:
                logger.debug(f"GStreamer превью ошибка: {stderr.decode(errors='replace')}")
                return None

            return stdout if stdout else None

        except Exception as e:
            logger.error(f"Ошибка GStreamer превью: {e}")
            return None

    def _get_encoder(self, fmt: PreviewFormat, quality: int) -> str:
        if fmt == PreviewFormat.JPEG:
            return f"jpegenc quality={quality}"
        elif fmt == PreviewFormat.PNG:
            return "pngenc"
        elif fmt == PreviewFormat.WEBP:
            return f"webpenc quality={quality}"
        elif fmt == PreviewFormat.TIFF:
            return "tiffenc"
        return "jpegenc"

    def _source_element(self, url: str, protocol: StreamProtocol) -> str:
        # Для превью лучше использовать souphttpsrc для http или rtspsrc
        if protocol == StreamProtocol.UDP:
            addr = url.replace("udp://", "").replace("@", "")
            host, port = addr.split(":") if ":" in addr else (addr, "1234")
            return f"udpsrc address={host} port={port}"
        elif protocol == StreamProtocol.RTSP:
            return f"rtspsrc location={url}"
        else:
            return f"souphttpsrc location={url}"
