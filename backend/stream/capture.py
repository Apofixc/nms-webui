"""Захват одного кадра по URL потока (HTTP/UDP). Бэкенды: FFmpeg, VLC, GStreamer."""
from __future__ import annotations

import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from backend.utils import find_executable


class CaptureBackend(ABC):
    """Абстрактный бэкенд захвата кадра по URL."""

    @classmethod
    def available(cls) -> bool:
        """Проверка, доступен ли бэкенд в системе."""
        raise NotImplementedError

    @abstractmethod
    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
    ) -> bytes:
        """Захватить один кадр. При ошибке — исключение или пустой bytes."""
        raise NotImplementedError


class FFmpegCaptureBackend(CaptureBackend):
    """Захват кадра через FFmpeg (subprocess). Поддерживает HTTP и UDP."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg"):
        self.ffmpeg_bin = find_executable(ffmpeg_bin) or ffmpeg_bin

    @classmethod
    def available(cls, ffmpeg_bin: str = "ffmpeg") -> bool:
        return find_executable(ffmpeg_bin) is not None

    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
    ) -> bytes:
        ext = "jpg" if output_format == "jpeg" else output_format
        out_file = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
        out_file.close()
        # UDP: формат mpegts задаём явно, иначе FFmpeg долго буферизует при автоопределении
        is_udp = isinstance(url, str) and url.strip().lower().startswith("udp")
        wait_sec = (timeout_sec + 10.0) if is_udp else timeout_sec
        try:
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-timeout", str(int(wait_sec * 1_000_000)),
                "-protocol_whitelist", "file,http,https,tcp,tls,udp",
            ]
            if is_udp:
                # Меньше буфера для анализа — быстрее первый кадр; формат mpegts задан явно
                cmd.extend(["-analyzeduration", "500000", "-probesize", "500000", "-f", "mpegts", "-i", url])
            else:
                cmd.extend(["-i", url])
            cmd.extend([
                "-vframes", "1",
                "-f", "image2",
                out_file.name,
            ])
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=wait_sec + 2,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg failed: {proc.stderr.decode(errors='replace') or proc.stdout.decode(errors='replace')}"
                )
            return Path(out_file.name).read_bytes()
        finally:
            Path(out_file.name).unlink(missing_ok=True)


class VLCCaptureBackend(CaptureBackend):
    """Захват кадра через VLC (subprocess). Резервный вариант."""

    def __init__(self, vlc_bin: str = "vlc"):
        self.vlc_bin = find_executable(vlc_bin) or vlc_bin

    @classmethod
    def available(cls, vlc_bin: str = "vlc") -> bool:
        return find_executable(vlc_bin) is not None

    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
    ) -> bytes:
        out_dir = tempfile.mkdtemp()
        out_path = Path(out_dir) / f"frame.{output_format}"
        try:
            cmd = [
                self.vlc_bin,
                "-I", "dummy",
                "--no-video-title-show",
                "--run-time=2",
                "--vout=vdummy",
                "--no-audio",
                f"--scene-format={output_format}",
                f"--scene-path={out_dir}",
                "--scene-ratio=1",
                url,
                "vlc://quit",
            ]
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout_sec + 5,
            )
            if out_path.exists():
                return out_path.read_bytes()
            raise RuntimeError("VLC did not produce output frame")
        finally:
            import shutil as _shutil
            _shutil.rmtree(out_dir, ignore_errors=True)


class GStreamerCaptureBackend(CaptureBackend):
    """Захват кадра через GStreamer (gst-launch-1.0). Резервный вариант."""

    def __init__(self, gst_launch: str = "gst-launch-1.0"):
        self.gst_launch = find_executable(gst_launch) or gst_launch

    @classmethod
    def available(cls, gst_launch: str = "gst-launch-1.0") -> bool:
        return find_executable(gst_launch) is not None

    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
    ) -> bytes:
        out_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        out_file.close()
        try:
            # uridecodebin -> videoconvert -> jpegenc -> filesink
            pipeline = (
                f"uridecodebin uri={url!r} ! "
                "videoconvert ! "
                "jpegenc ! "
                f"filesink location={out_file.name}"
            )
            cmd = [self.gst_launch, "-e", pipeline]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout_sec + 2,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"GStreamer failed: {proc.stderr.decode(errors='replace')}"
                )
            data = Path(out_file.name).read_bytes()
            if not data:
                raise RuntimeError("GStreamer produced empty output")
            return data
        finally:
            Path(out_file.name).unlink(missing_ok=True)


# Порядок попытки бэкендов
DEFAULT_CAPTURE_BACKENDS: list[type[CaptureBackend]] = [
    FFmpegCaptureBackend,
    VLCCaptureBackend,
    GStreamerCaptureBackend,
]


class StreamFrameCapture:
    """
    Фасад захвата одного кадра по URL потока (HTTP/UDP).
    Выбирает первый доступный бэкенд: FFmpeg → VLC → GStreamer.
    """

    def __init__(
        self,
        backends: Optional[list[type[CaptureBackend]]] = None,
    ):
        self._backends = backends or DEFAULT_CAPTURE_BACKENDS
        self._backend: Optional[CaptureBackend] = None
        self._resolve_backend()

    def _resolve_backend(self) -> None:
        for backend_cls in self._backends:
            if backend_cls.available():
                self._backend = backend_cls()
                return
        self._backend = None

    @property
    def available(self) -> bool:
        """Есть ли хотя бы один доступный бэкенд."""
        return self._backend is not None

    @property
    def backend_name(self) -> str:
        """Имя текущего бэкенда."""
        if self._backend is None:
            return "none"
        return self._backend.__class__.__name__.replace("CaptureBackend", "").lower()

    def capture(
        self,
        url: str,
        *,
        timeout_sec: float = 10.0,
        output_format: str = "jpeg",
    ) -> bytes:
        """
        Захватить один кадр по URL.
        :raises RuntimeError: если нет доступного бэкенда или захват не удался.
        """
        if self._backend is None:
            raise RuntimeError(
                "No capture backend available. Install ffmpeg, vlc, or gstreamer."
            )
        return self._backend.capture(
            url,
            timeout_sec=timeout_sec,
            output_format=output_format,
        )
