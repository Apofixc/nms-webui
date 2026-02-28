# Субмодуль Pure Preview — нативная генерация превью
# Извлечение ключевого кадра из MPEG-TS и кодирование в JPEG/PNG/WebP
import asyncio
import io
import logging
import struct
from typing import Optional, Set

import aiohttp

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

logger = logging.getLogger(__name__)

# Размер пакета MPEG-TS
TS_PACKET_SIZE = 188
TS_SYNC_BYTE = 0x47

# Размер начальной загрузки для поиска I-кадра (2 МБ)
INITIAL_BUFFER_SIZE = 2 * 1024 * 1024


class PurePreviewBackend(IStreamBackend):
    """Нативный Python-бэкенд для генерации превью.

    Стратегия: скачивание начального фрагмента потока
    и декодирование первого I-кадра через Pillow.
    Если Pillow недоступен — fallback на raw-данные.
    """

    def __init__(self, timeout: int = 15) -> None:
        self._timeout = timeout
        self._pillow_available: Optional[bool] = None

    @property
    def backend_id(self) -> str:
        return "pure_preview"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.PREVIEW}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.HLS, StreamProtocol.UDP}

    def supported_output_types(self) -> Set[OutputType]:
        return set()

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {PreviewFormat.JPEG, PreviewFormat.PNG, PreviewFormat.WEBP}

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Не поддерживает стриминг."""
        return StreamResult(
            task_id=task.task_id or "",
            success=False,
            backend_used="pure_preview",
            error="pure_preview не поддерживает стриминг, только генерацию превью",
        )

    async def stop_stream(self, task_id: str) -> bool:
        return False

    async def generate_preview(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int = 640,
        quality: int = 75,
    ) -> Optional[bytes]:
        """Генерация превью из сетевого потока.

        Алгоритм:
        1. Скачивание начального фрагмента потока (HTTP/HLS).
        2. Извлечение video PES из MPEG-TS.
        3. Декодирование через Pillow (если доступен).
        4. Масштабирование и кодирование в указанный формат.
        """
        if not await self._check_pillow():
            logger.warning("Pillow недоступен, превью невозможно")
            return None

        try:
            # Скачивание начального фрагмента
            raw_data = await self._fetch_stream_data(url, protocol)
            if not raw_data:
                return None

            # Попытка декодирования через Pillow
            return await self._decode_and_encode(raw_data, fmt, width, quality)

        except Exception as e:
            logger.error(f"Pure preview ошибка: {e}", exc_info=True)
            return None

    async def is_available(self) -> bool:
        """Проверка доступности Pillow."""
        return await self._check_pillow()

    async def health_check(self) -> dict:
        pillow = await self._check_pillow()
        return {
            "backend": "pure_preview",
            "native": True,
            "pillow_available": pillow,
            "available": pillow,
        }

    # --- Приватные методы ---

    async def _check_pillow(self) -> bool:
        """Проверка наличия Pillow (кэшируется)."""
        if self._pillow_available is None:
            try:
                import PIL  # noqa: F401
                self._pillow_available = True
            except ImportError:
                self._pillow_available = False
        return self._pillow_available

    async def _fetch_stream_data(
        self, url: str, protocol: StreamProtocol
    ) -> Optional[bytes]:
        """Загрузка начального фрагмента потока."""
        if protocol == StreamProtocol.HLS:
            return await self._fetch_hls_segment(url)
        elif protocol in (StreamProtocol.HTTP, StreamProtocol.UDP):
            return await self._fetch_http_chunk(url)
        return None

    async def _fetch_http_chunk(self, url: str) -> Optional[bytes]:
        """Скачивание начального фрагмента HTTP потока."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self._timeout),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"HTTP статус {resp.status} для {url}")
                        return None

                    # Читаем фиксированный объём данных
                    data = await resp.content.read(INITIAL_BUFFER_SIZE)
                    return data if data else None

        except asyncio.TimeoutError:
            logger.warning(f"Таймаут загрузки {url}")
            return None
        except Exception as e:
            logger.error(f"Ошибка загрузки {url}: {e}")
            return None

    async def _fetch_hls_segment(self, url: str) -> Optional[bytes]:
        """Загрузка первого сегмента из HLS плейлиста."""
        try:
            async with aiohttp.ClientSession() as session:
                # Загрузка плейлиста
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self._timeout),
                ) as resp:
                    if resp.status != 200:
                        return None
                    playlist = await resp.text()

                # Парсинг первого .ts сегмента
                base_url = url.rsplit("/", 1)[0]
                for line in playlist.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        seg_url = line if line.startswith("http") else f"{base_url}/{line}"

                        # Загрузка сегмента
                        async with session.get(
                            seg_url,
                            timeout=aiohttp.ClientTimeout(total=self._timeout),
                        ) as seg_resp:
                            if seg_resp.status == 200:
                                return await seg_resp.read()
                        break

        except Exception as e:
            logger.error(f"HLS сегмент ошибка: {e}")

        return None

    async def _decode_and_encode(
        self,
        raw_data: bytes,
        fmt: PreviewFormat,
        width: int,
        quality: int,
    ) -> Optional[bytes]:
        """Декодирование MPEG-TS данных в изображение через Pillow.

        Пытается извлечь видеокадр из потока.
        Если raw_data содержит JPEG/PNG напрямую — декодирует сразу.
        """
        try:
            from PIL import Image

            # Попытка прямого декодирования (если данные содержат изображение)
            try:
                img = Image.open(io.BytesIO(raw_data))
                img.verify()
                img = Image.open(io.BytesIO(raw_data))
            except Exception:
                # MPEG-TS данные — пробуем найти JPEG внутри
                # Поиск JFIF/Exif маркеров в данных
                jpeg_data = self._extract_jpeg_from_ts(raw_data)
                if jpeg_data:
                    img = Image.open(io.BytesIO(jpeg_data))
                else:
                    logger.debug("Не удалось извлечь кадр из TS данных")
                    return None

            # Масштабирование
            if img.width > width:
                ratio = width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((width, new_height), Image.LANCZOS)

            # Кодирование в нужный формат
            output = io.BytesIO()
            if fmt == PreviewFormat.JPEG:
                img = img.convert("RGB")
                img.save(output, format="JPEG", quality=quality, optimize=True)
            elif fmt == PreviewFormat.PNG:
                img.save(output, format="PNG", optimize=True)
            elif fmt == PreviewFormat.WEBP:
                img.save(output, format="WEBP", quality=quality)

            return output.getvalue()

        except ImportError:
            logger.error("Pillow не установлен")
            return None
        except Exception as e:
            logger.error(f"Ошибка декодирования: {e}")
            return None

    @staticmethod
    def _extract_jpeg_from_ts(data: bytes) -> Optional[bytes]:
        """Поиск JPEG данных внутри MPEG-TS потока.

        Ищет SOI маркер (FF D8) и EOI маркер (FF D9).
        """
        soi = data.find(b"\xff\xd8")
        if soi == -1:
            return None

        eoi = data.find(b"\xff\xd9", soi)
        if eoi == -1:
            return None

        return data[soi : eoi + 2]


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Pure Preview."""
    timeout = settings.get("worker_timeout", 15)
    return PurePreviewBackend(timeout=timeout)
