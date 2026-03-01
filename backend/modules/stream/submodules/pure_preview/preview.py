# Нативная логика генерации превью (PyAV + Pillow)
import asyncio
import io
import logging
import re
from typing import Optional

from backend.modules.stream.core.types import StreamProtocol, PreviewFormat

logger = logging.getLogger(__name__)


class PurePreviewer:
    """Нативный генератор превью на базе PyAV.

    Все параметры берутся из settings с поддержкой префикса pure_preview_.
    """

    def __init__(self, settings: dict):
        self.settings = settings
        self.timeout = int(settings.get("pure_preview_timeout") or settings.get("timeout", 15))
        self.resize_method = settings.get("pure_preview_resize_method") or settings.get("resize_method", "LANCZOS")
        
        logger.debug(f"PurePreviewer initialized: timeout={self.timeout}, resize={self.resize_method}")

    async def generate(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int = 640,
        quality: int = 75
    ) -> Optional[bytes]:
        """Генерация превью путем декодирования первого попавшегося видео-кадра."""
        
        clean_url = url.split("#", 1)[0] if "#" in url else url
        if "://0:" in clean_url:
            clean_url = clean_url.replace("://0:", "://127.0.0.1:")

        # Специфичная обработка для UDP
        if clean_url.startswith("udp://"):
            # Проверяем, является ли адрес мультикастным (224.0.0.0 - 239.255.255.255)
            # Если да, и нет @, добавляем его
            match = re.search(r'udp://(\d+)\.', clean_url)
            if match:
                first_octet = int(match.group(1))
                if 224 <= first_octet <= 239 and "@" not in clean_url:
                    clean_url = clean_url.replace("udp://", "udp://@")
            
            # Добавляем параметры для возможности совместного использования порта (reuse=1)
            # и увеличения буфера, чтобы не терять пакеты
            sep = "?" if "?" not in clean_url else "&"
            if "reuse=" not in clean_url:
                clean_url += f"{sep}reuse=1"
                sep = "&"
            if "fifo_size=" not in clean_url:
                clean_url += f"{sep}fifo_size=1000000"
                sep = "&"
            if "buffer_size=" not in clean_url:
                clean_url += f"{sep}buffer_size=10000000"

        logger.info(f"Начало генерации превью через pure_preview: {clean_url}")
        try:
            return await asyncio.to_thread(self._generate_sync, clean_url, protocol, fmt, width, quality)
        except Exception as e:
            logger.error(f"Ошибка в generate (async): {e}")
            return None

    def _generate_sync(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int,
        quality: int
    ) -> Optional[bytes]:
        try:
            import av
            from PIL import Image
        except ImportError as e:
            logger.warning(f"Библиотеки av или Pillow не установлены: {e}")
            return None

        container = None
        try:
            # Опции декодера
            options = {
                "probesize": "2000000", 
                "analyzeduration": "2000000",
                "fflags": "nobuffer",
                "flags": "low_delay",
            }
            
            if url.startswith("rtsp"):
                options["rtsp_transport"] = "tcp"
            
            # Для UDP таймаут передаем через stimeout (в микросекундах)
            if "udp://" in url:
                options["stimeout"] = str(int(self.timeout * 1000000))

            # Открываем контейнер с явным таймаутом открытия (timeout в секундах для av.open)
            container = av.open(url, options=options, timeout=self.timeout)
            
            video_stream = next((s for s in container.streams if s.type == "video"), None)
            if not video_stream:
                logger.debug(f"Видеопоток не найден в {url}")
                return None

            # Декодируем пакеты
            # Ограничиваем количество пакетов, чтобы не висеть вечно если кадров нет
            max_packets = 100
            packet_count = 0
            
            for packet in container.demux(video_stream):
                packet_count += 1
                if packet_count > max_packets:
                    break
                    
                if packet.size == 0:
                    continue

                try:
                    for frame in packet.decode():
                        # Берем первый же успешно декодированный кадр
                        img = frame.to_image()
                        
                        # Ресайз
                        if img.width > width:
                            resample = self.resize_method
                            if isinstance(resample, str):
                                 if hasattr(Image, 'Resampling'):
                                     resample = getattr(Image.Resampling, resample, Image.Resampling.LANCZOS)
                                 else:
                                     resample = getattr(Image, resample, Image.LANCZOS)
                            
                            ratio = width / img.width
                            img = img.resize((width, int(img.height * ratio)), resample)

                        # Конвертация формата
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
                        logger.info(f"Превью успешно создано для {url} ({len(output.getvalue())} байт)")
                        return output.getvalue()
                except (av.AVError, UnicodeDecodeError):
                    continue 

        except Exception as e:
            logger.error(f"PyAV sync error for {url}: {e}")
        finally:
            if container:
                try:
                    container.close()
                except:
                    pass
        
        return None
