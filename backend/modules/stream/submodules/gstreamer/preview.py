# Логика генерации превью через GStreamer
import asyncio
import logging
import shlex
from typing import Optional, List

from backend.modules.stream.core.types import StreamProtocol, PreviewFormat

logger = logging.getLogger(__name__)


class GStreamerPreviewer:
    """Генератор превью на базе GStreamer.

    Поддерживает override-шаблон для полной кастомизации.
    """

    def __init__(self, settings: dict):
        self.binary_path = settings.get("binary_path", "gst-launch-1.0")
        self.preview_framerate = settings.get("preview_framerate", "1/1")
        self.udp_default_port = settings.get("udp_default_port", 5000)

        # Override
        self.override_preview = settings.get("override_preview", "")

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

        # Override-шаблон
        if self.override_preview:
            pipeline = self._apply_override(src, width, encoder)
            if pipeline:
                return await self._execute(pipeline)

        # Штатный пайплайн: один кадр -> stdout
        pipeline = (
            f"{src} ! decodebin ! videoconvert ! videoscale ! videorate ! "
            f"video/x-raw,width={width},framerate={self.preview_framerate} ! "
            f"{encoder} ! fdsink fd=1"
        )

        return await self._execute(pipeline)

    def _get_encoder(self, fmt: PreviewFormat, quality: int) -> str:
        if fmt in (PreviewFormat.AUTO, PreviewFormat.JPEG):
            return f"jpegenc quality={quality}"
        elif fmt == PreviewFormat.PNG:
            return "pngenc"
        elif fmt == PreviewFormat.WEBP:
            return f"webpenc quality={quality}"
        elif fmt == PreviewFormat.TIFF:
            return "tiffenc"
        return f"jpegenc quality={quality}"

    def _source_element(self, url: str, protocol: StreamProtocol) -> str:
        if protocol == StreamProtocol.UDP:
            addr = url.replace("udp://", "").replace("@", "")
            host, port = addr.split(":") if ":" in addr else (addr, str(self.udp_default_port))
            return f"udpsrc address={host} port={port}"
        elif protocol == StreamProtocol.RTSP:
            return f"rtspsrc location={url}"
        elif protocol == StreamProtocol.SRT:
            return f'srtsrc uri="{url}"'
        else:
            return f"souphttpsrc location={url}"

    def _apply_override(self, source: str, width: int, encoder: str) -> Optional[str]:
        """Подстановка переменных в override-шаблон."""
        try:
            return self.override_preview.format(
                source=source,
                width=width,
                encoder=encoder,
            )
        except (KeyError, ValueError) as e:
            logger.warning(f"Ошибка в override-шаблоне превью GStreamer: {e}")
            return None

    async def _execute(self, pipeline: str) -> Optional[bytes]:
        """Запуск GStreamer пайплайна и получение результата."""
        cmd = [self.binary_path, "-e"] + shlex.split(pipeline)

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
