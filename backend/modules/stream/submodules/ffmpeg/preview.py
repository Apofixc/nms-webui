# Логика генерации превью через FFmpeg
import asyncio
import logging
import shlex
from typing import Optional, List

from backend.modules.stream.core.types import StreamProtocol, PreviewFormat

logger = logging.getLogger(__name__)


class FFmpegPreviewer:
    """Генератор превью на базе FFmpeg.

    Поддерживает override-шаблон для полной настройки команды.
    """

    def __init__(self, settings: dict):
        self.binary_path = settings.get("binary_path", "ffmpeg")

        raw_args = settings.get("global_args", "-hide_banner -loglevel error")
        self.global_args = raw_args.split() if isinstance(raw_args, str) else (raw_args or [])

        # Параметры превью
        self.preview_timeout = settings.get("preview_timeout", 2)
        self.preview_vframes = settings.get("preview_vframes", 1)
        self.rtsp_transport = settings.get("rtsp_transport", "tcp")

        # Override-шаблон
        self.override_preview = settings.get("override_preview", "")

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

        # Override-шаблон
        if self.override_preview:
            cmd = self._from_override(url, width, quality, f_name)
            if cmd:
                return await self._execute(cmd, url)

        # Штатная сборка команды
        cmd = [self.binary_path] + self.global_args

        # Опции входа
        if protocol == StreamProtocol.RTSP:
            cmd.extend(["-rtsp_transport", self.rtsp_transport])

        # Читаем только N секунд потока для поиска первого кадра
        cmd.extend(["-t", str(self.preview_timeout), "-i", url])

        # Настройка кадра
        cmd.extend([
            "-frames:v", str(self.preview_vframes),
            "-vf", f"scale={width}:-1",
        ])

        # Качество для форматов, которые его поддерживают
        if fmt in (PreviewFormat.JPEG, PreviewFormat.WEBP):
            cmd.extend(["-q:v", str(max(1, min(31, 31 - int(quality * 0.3))))])

        cmd.extend(["-f", f_name, "pipe:1"])

        return await self._execute(cmd, url)

    def _from_override(self, url: str, width: int, quality: int, fmt: str) -> Optional[List[str]]:
        """Подстановка переменных в override-шаблон."""
        try:
            rendered = self.override_preview.format(
                binary_path=self.binary_path,
                global_args=" ".join(self.global_args),
                input_url=url,
                width=width,
                quality=quality,
                format=fmt
            )
            return shlex.split(rendered)
        except (KeyError, ValueError) as e:
            logger.warning(f"Ошибка в override-шаблоне превью: {e}. Используется штатная логика.")
            return None

    async def _execute(self, cmd: List[str], url: str) -> Optional[bytes]:
        """Запуск FFmpeg и получение результата."""
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
                logger.warning(f"Таймаут генерации превью FFmpeg для {url}")
                return None

            if process.returncode != 0:
                logger.debug(f"FFmpeg превью ошибка: {stderr.decode(errors='replace')}")
                return None

            return stdout if stdout else None

        except Exception as e:
            logger.error(f"Ошибка FFmpeg превью: {e}")
            return None
