# Нативная логика генерации превью (Pillow + MPEG-TS)
import asyncio
import io
import logging
import aiohttp
from typing import Optional

from backend.modules.stream.core.types import StreamProtocol, PreviewFormat

logger = logging.getLogger(__name__)


class PurePreviewer:
    """Нативный генератор превью.

    Все параметры (timeout, buffer, resize method) берутся из settings.
    """

    def __init__(self, settings: dict):
        self.timeout = settings.get("timeout", 15)
        self.buffer_size = settings.get("initial_buffer_size", 2097152)
        self.resize_method = settings.get("resize_method", "LANCZOS")

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
        jpeg_data = self._extract_jpeg(data)
        if not jpeg_data:
            return None

        # 3. Обработка изображения
        try:
            img = Image.open(io.BytesIO(jpeg_data))

            # Масштабирование с выбранным методом интерполяции
            if img.width > width:
                resample = getattr(Image, self.resize_method, Image.LANCZOS)
                ratio = width / img.width
                img = img.resize((width, int(img.height * ratio)), resample)

            # Выбор формата
            format_map = {
                PreviewFormat.JPEG: "JPEG",
                PreviewFormat.PNG: "PNG",
                PreviewFormat.WEBP: "WEBP",
            }
            img_format = format_map.get(fmt, "JPEG")

            output = io.BytesIO()
            save_kwargs = {"format": img_format}
            if img_format in ("JPEG", "WEBP"):
                save_kwargs["quality"] = quality
            img.save(output, **save_kwargs)
            return output.getvalue()

        except Exception as e:
            logger.error(f"Ошибка Pillow: {e}")
            return None

    async def _fetch_data(self, url: str, protocol: StreamProtocol) -> Optional[bytes]:
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.content.read(self.buffer_size)
        except Exception as e:
            logger.debug(f"Ошибка загрузки данных для превью: {e}")
        return None

    def _extract_jpeg(self, data: bytes) -> Optional[bytes]:
        start = data.find(b"\xff\xd8")
        if start == -1:
            return None
        end = data.find(b"\xff\xd9", start)
        if end == -1:
            return None
        return data[start:end + 2]
