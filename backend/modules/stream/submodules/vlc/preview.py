# Логика генерации превью через VLC
import asyncio
import logging
import os
import shutil
import tempfile
from typing import Optional

from backend.modules.stream.core.types import StreamProtocol, PreviewFormat

logger = logging.getLogger(__name__)


class VLCPreviewer:
    """Генератор превью на базе VLC scene filter."""

    def __init__(self, settings: dict):
        self.binary_path = settings.get("binary_path", "cvlc")
        self.scene_ratio = settings.get("scene_ratio", 10)
        self.scene_run_time = settings.get("scene_run_time", 5)

    async def generate(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int = 640,
        quality: int = 75
    ) -> Optional[bytes]:

        # VLC генерирует файлы на диск через scene filter
        tmp_dir = tempfile.mkdtemp(prefix="vlc_pre_")
        ext = "jpg" if fmt == PreviewFormat.JPEG else "png"

        cmd = [
            self.binary_path,
            url,
            "--no-audio",
            "--play-and-exit",
            f"--run-time={self.scene_run_time}",
            "--video-filter=scene",
            f"--scene-format={ext}",
            f"--scene-ratio={self.scene_ratio}",
            f"--scene-path={tmp_dir}",
            "--scene-prefix=snap",
            "--vout=dummy",
            "--aout=dummy"
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            try:
                await asyncio.wait_for(process.wait(), timeout=20)
            except asyncio.TimeoutError:
                process.kill()

            # Ищем созданный файл
            for f_name in os.listdir(tmp_dir):
                if f_name.startswith("snap"):
                    f_path = os.path.join(tmp_dir, f_name)
                    with open(f_path, "rb") as f:
                        return f.read()

            return None

        except Exception as e:
            logger.error(f"Ошибка VLC превью: {e}")
            return None
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
