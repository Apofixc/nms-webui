# Нативная логика генерации превью (Pillow + MPEG-TS)
import asyncio
import io
import logging
import aiohttp
from typing import Optional

from backend.modules.stream.core.types import StreamProtocol, PreviewFormat

logger = logging.getLogger(__name__)


class PurePreviewer:
    """Нативный генератор превью."""

    def __init__(self, timeout: int = 15, buffer_size: int = 2097152):
        self.timeout = timeout
        self.buffer_size = buffer_size

    async def generate(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int = 640,
        quality: int = 75
    ) -> Optional[bytes]:
        
        try:
            from PIL import Image
        except ImportError:
            logger.warning("Pillow не установлен, Pure Preview недоступен")
            return None

        # 1. Загрузка данных
        data = await self._fetch_data(url, protocol)
        if not data:
            return None

        # 2. Поиск JPEG внутри потока (SOI FF D8, EOI FF D9)
        # Это упрощенный метод для MJPEG/TS
        jpeg_data = self._extract_jpeg(data)
        if not jpeg_data:
            return None

        # 3. Обработка изображения
        try:
            img = Image.open(io.BytesIO(jpeg_data))
            if img.width > width:
                ratio = width / img.width
                img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
            
            output = io.BytesIO()
            img_format = "JPEG" if fmt == PreviewFormat.JPEG else "PNG"
            img.save(output, format=img_format, quality=quality)
            return output.getvalue()
        except Exception as e:
            logger.error(f"Ошибка Pillow: {e}")
            return None

    async def _fetch_data(self, url: str, protocol: StreamProtocol) -> Optional[bytes]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        return await resp.content.read(self.buffer_size)
        except Exception as e:
            logger.debug(f"Ошибка загрузки данных для превью: {e}")
        return None

    def _extract_jpeg(self, data: bytes) -> Optional[bytes]:
        start = data.find(b"\xff\xd8")
        if start == -1: return None
        end = data.find(b"\xff\xd9", start)
        if end == -1: return None
        return data[start:end+2]
