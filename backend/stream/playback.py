"""Сессия просмотра потока в браузере: HTTP прокси или UDP→HTTP (FFmpeg pipe / in-code proxy)."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from backend.utils import find_executable

from backend.stream.udp_to_http import is_udp_url as _is_udp_url


def is_http_url(url: str) -> bool:
    return isinstance(url, str) and (
        url.startswith("http://") or url.startswith("https://")
    )


def is_udp_url(url: str) -> bool:
    return _is_udp_url(url)


class PlaybackBackend(ABC):
    """Бэкенд конвертации потока для просмотра в браузере."""

    @classmethod
    def available(cls) -> bool:
        raise NotImplementedError

    @abstractmethod
    def start(self, source_url: str, output_dir: Path, session_id: str) -> str:
        """Запустить конвертацию. Вернуть относительный путь к playlist.m3u8 (например streams/{id}/playlist.m3u8)."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Остановить процесс."""
        raise NotImplementedError

    @abstractmethod
    def is_alive(self) -> bool:
        raise NotImplementedError


class FFmpegPlaybackBackend(PlaybackBackend):
    """UDP/HTTP → HLS через FFmpeg. Пишет сегменты в output_dir."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg"):
        self.ffmpeg_bin = find_executable(ffmpeg_bin) or ffmpeg_bin
        self._process: Optional[subprocess.Popen] = None
        self._output_dir: Optional[Path] = None

    @classmethod
    def available(cls, ffmpeg_bin: str = "ffmpeg") -> bool:
        return find_executable(ffmpeg_bin) is not None

    def start(self, source_url: str, output_dir: Path, session_id: str) -> str:
        session_dir = output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = session_dir / "playlist.m3u8"
        # HLS: короткие сегменты для меньшей задержки; copy без перекодирования
        cmd = [
            self.ffmpeg_bin,
            "-protocol_whitelist", "file,http,https,tcp,tls,udp",
            "-i", source_url,
            "-c", "copy",
            "-f", "hls",
            "-hls_time", "1",
            "-hls_list_size", "3",
            "-hls_flags", "delete_segments+append_list",
            "-hls_segment_filename", str(session_dir / "seg_%03d.ts"),
            str(playlist_path),
        ]
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self._output_dir = session_dir
        return f"streams/{session_id}/playlist.m3u8"

    def stop(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None
        self._output_dir = None

    def is_alive(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def get_playlist_path(self) -> Optional[Path]:
        return self._output_dir / "playlist.m3u8" if self._output_dir else None


class VLCPlaybackBackend(PlaybackBackend):
    """Резервный бэкенд через VLC (трансляция в HTTP). Пока заглушка."""

    @classmethod
    def available(cls) -> bool:
        return shutil.which("vlc") is not None

    def start(self, source_url: str, output_dir: Path, session_id: str) -> str:
        raise NotImplementedError("VLC playback backend not implemented yet")

    def stop(self) -> None:
        pass

    def is_alive(self) -> bool:
        return False


class GStreamerPlaybackBackend(PlaybackBackend):
    """Резервный бэкенд через GStreamer. Пока заглушка."""

    @classmethod
    def available(cls) -> bool:
        return shutil.which("gst-launch-1.0") is not None

    def start(self, source_url: str, output_dir: Path, session_id: str) -> str:
        raise NotImplementedError("GStreamer playback backend not implemented yet")

    def stop(self) -> None:
        pass

    def is_alive(self) -> bool:
        return False


class AstraPlaybackBackend(PlaybackBackend):
    """
    Опциональный бэкенд: создание потока в Astra с UDP-входом и HTTP-выходом.
    Требует Astra API (instance_id, base_url, api_key). Пока заглушка.
    """

    def __init__(self, instance_id: int, base_url: str, api_key: str):
        self.instance_id = instance_id
        self.base_url = base_url
        self.api_key = api_key

    @classmethod
    def available(cls) -> bool:
        return True  # доступность проверяется по наличию Astra при вызове

    def start(self, source_url: str, output_dir: Path, session_id: str) -> str:
        raise NotImplementedError(
            "Astra playback backend: create stream via API and return HTTP Play URL"
        )

    def stop(self) -> None:
        pass

    def is_alive(self) -> bool:
        return False


DEFAULT_PLAYBACK_BACKENDS: list[type[PlaybackBackend]] = [
    FFmpegPlaybackBackend,
]


class StreamPlaybackSession:
    """
    Сессия просмотра потока в браузере.
    - Если source_url уже http(s) — возвращаем его без конвертации.
    - Иначе запускаем конвертацию (FFmpeg → VLC → Astra → GStreamer) и возвращаем URL плейлиста.
    """

    def __init__(
        self,
        output_base_dir: Optional[Path] = None,
        backends: Optional[list[type[PlaybackBackend]]] = None,
    ):
        self._output_base = output_base_dir or Path(tempfile.gettempdir()) / "nms_streams"
        self._output_base.mkdir(parents=True, exist_ok=True)
        self._backends = backends or DEFAULT_PLAYBACK_BACKENDS
        self._backend_instance: Optional[PlaybackBackend] = None
        self._session_id: Optional[str] = None
        self._playlist_relative: Optional[str] = None
        self._ready_http_url: Optional[str] = None  # если URL уже HTTP
        self._udp_url: Optional[str] = None  # UDP → стримим по HTTP (TS или HLS)
        self._live_hls_dir: Optional[Path] = None  # при UDP+HLS: каталог с playlist.m3u8 и сегментами
        self._live_hls_process: Optional[Any] = None  # процесс FFmpeg (или иной) для UDP→HLS

    def start(self, source_url: str) -> str:
        """
        Запустить просмотр. Вернуть URL для плеера.
        - HTTP (с .m3u8 или сырой MPEG-TS) → прокси; воспроизведение через mpegts.js или нативно.
        - UDP → /api/streams/live/{id}/ (сырой MPEG-TS по HTTP, FFmpeg или in-code proxy).
        """
        if is_http_url(source_url):
            self._ready_http_url = source_url
            self._session_id = str(uuid.uuid4())[:8]
            return f"/api/streams/proxy/{self._session_id}/"

        if is_udp_url(source_url):
            self._udp_url = source_url
            self._session_id = str(uuid.uuid4())[:8]
            return f"/api/streams/live/{self._session_id}"

        backend_cls = None
        for cls in self._backends:
            if cls.available():
                backend_cls = cls
                break
        if backend_cls is None:
            raise RuntimeError(
                "No playback backend available for conversion. Install ffmpeg."
            )

        self._session_id = str(uuid.uuid4())[:8]
        self._backend_instance = backend_cls()
        self._playlist_relative = self._backend_instance.start(
            source_url,
            self._output_base,
            self._session_id,
        )
        return f"/api/{self._playlist_relative}"

    def stop(self) -> None:
        """Остановить сессию и процесс конвертации."""
        if self._live_hls_process is not None:
            try:
                if self._live_hls_process.poll() is None:
                    self._live_hls_process.terminate()
                    self._live_hls_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, Exception):
                try:
                    self._live_hls_process.kill()
                except Exception:
                    pass
            self._live_hls_process = None
        self._live_hls_dir = None
        if self._backend_instance is not None:
            self._backend_instance.stop()
            self._backend_instance = None
        self._session_id = None
        self._playlist_relative = None
        self._ready_http_url = None
        self._udp_url = None

    def is_alive(self) -> bool:
        """Активна ли сессия. Для HTTP/UDP (прокси или live) всегда True до stop()."""
        if self._ready_http_url is not None or self._udp_url is not None:
            return True
        if self._backend_instance is None:
            return False
        return self._backend_instance.is_alive()

    def get_udp_url(self) -> Optional[str]:
        """URL UDP-потока (для стриминга в GET /api/streams/live/...)."""
        return self._udp_url

    def get_playlist_path(self) -> Optional[Path]:
        """Путь к playlist.m3u8 на диске (для раздачи через FileResponse). Для UDP-сессий без HLS — None."""
        if self._live_hls_dir is not None:
            return self._live_hls_dir / "playlist.m3u8"
        if not self._session_id or not self._output_base or self._udp_url is not None:
            return None
        return self._output_base / self._session_id / "playlist.m3u8"

    def get_session_dir(self) -> Optional[Path]:
        """Каталог сессии (для раздачи сегментов). Для UDP без HLS — None."""
        if self._live_hls_dir is not None:
            return self._live_hls_dir
        if not self._session_id or not self._output_base or self._udp_url is not None:
            return None
        return self._output_base / self._session_id

    def set_live_hls(self, session_dir: Path, process: Any) -> None:
        """Задать каталог и процесс для UDP→HLS (FFmpeg и т.п.)."""
        self._live_hls_dir = session_dir
        self._live_hls_process = process

    def get_http_base_url(self) -> Optional[str]:
        """Базовый URL для HTTP-потока (для проксирования сегментов HLS)."""
        if not self._ready_http_url:
            return None
        parts = self._ready_http_url.rsplit("/", 1)
        return (parts[0] + "/") if len(parts) == 2 else (self._ready_http_url + "/")

    def get_http_url(self) -> Optional[str]:
        """Полный URL HTTP-потока (манифест или прямой поток)."""
        return self._ready_http_url
