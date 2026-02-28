# Логика генерации превью через FFmpeg
import asyncio
import logging
from typing import Optional, List

from backend.modules.stream.core.types import StreamProtocol, PreviewFormat

logger = logging.getLogger(__name__)


class FFmpegPreviewer:
    """Генератор превью на базе FFmpeg."""

    def __init__(self, binary_path: str = "ffmpeg", global_args: List[str] = None):
        self.binary_path = binary_path
        self.global_args = global_args or ["-hide_banner", "-loglevel", "error"]

    async def generate(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int = 640,
        quality: int = 75
    ) -> Optional[bytes]:
        """Генерация одного кадра из потока."""
        
        # Маппинг форматов FFmpeg
        format_map = {
            PreviewFormat.JPEG: "mjpeg",
            PreviewFormat.PNG: "image2",
            PreviewFormat.WEBP: "webp",
            PreviewFormat.TIFF: "tiff",
            PreviewFormat.AVIF: "avif"
        }
        
        f_name = format_map.get(fmt, "mjpeg")

        cmd = [self.binary_path] + self.global_args
        
        # Опции входа
        if protocol == StreamProtocol.RTSP:
            cmd.extend(["-rtsp_transport", "tcp"])
        
        # Читаем только 2 секунды потока для поиска первого кадра
        cmd.extend(["-t", "2", "-i", url])
        
        # Настройка кадра: один кадр, масштаб
        cmd.extend([
            "-frames:v", "1",
            "-vf", f"scale={width}:-1",
            "-f", f_name,
            "pipe:1"
        ])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Читаем результат с таймаутом
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=15
                )
            except asyncio.TimeoutError:
                if process.returncode is None:
                    process.kill()
                logger.warning(f"Таймаут генерации превью FFmpeg для {url}")
                return None

            if process.returncode != 0:
                logger.debug(f"FFmpeg превью ошибка: {stderr.decode(errors='replace')}")
                return None

            return stdout if stdout else None

        except Exception as e:
            logger.error(f"Ошибка FFmpeg превью: {e}")
            return None
