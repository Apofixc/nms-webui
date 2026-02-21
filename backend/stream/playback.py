"""Сессия просмотра потока в браузере: HTTP → прокси, UDP → live (TS или HLS через main)."""
from __future__ import annotations

import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

from backend.stream.backends.udp_to_http import is_udp_url

__all__ = ["StreamPlaybackSession", "is_http_url", "is_udp_url", "get_input_format"]


def is_http_url(url: str) -> bool:
    """Проверка, что URL — HTTP или HTTPS."""
    return isinstance(url, str) and (
        url.startswith("http://") or url.startswith("https://")
    )


def get_input_format(url: str) -> str | None:
    """
    Определить входной формат по URL для выбора связки в реестре.
    Возвращает "udp", "http", "rtp", "rtsp", "srt", "hls", "tcp", "file" или None.
    """
    if not url or not isinstance(url, str):
        return None
    u = url.strip().lower()
    if is_udp_url(url.strip()):
        return "udp"
    if u.startswith("rtsp://"):
        return "rtsp"
    if u.startswith("rtp://"):
        return "rtp"
    if u.startswith("srt://"):
        return "srt"
    if u.startswith("tcp://"):
        return "tcp"
    if u.startswith("file://") or (u.startswith("/") and not u.startswith("//")):
        return "file"
    if is_http_url(url.strip()):
        if ".m3u8" in url.split("?")[0]:
            return "hls"
        return "http"
    return None


class StreamPlaybackSession:
    """
    Сессия просмотра потока.
    Поддерживаются все форматы из реестра (udp, http, rtp, rtsp, srt, hls, tcp, file).
    - HTTP без конвертации в HLS → proxy; HTTP → HLS (не .m3u8) → live (start_hls).
    - Остальные входы → всегда live (backend.stream или start_hls).
    """

    def __init__(self, output_base_dir: Optional[Path] = None):
        self._output_base = output_base_dir or Path(tempfile.gettempdir()) / "nms_streams"
        self._output_base.mkdir(parents=True, exist_ok=True)
        self._session_id: Optional[str] = None
        self._source_url: Optional[str] = None
        self._input_format: Optional[str] = None
        self._output_format: str = "http_ts"
        self._backend_name: Optional[str] = None
        self._backend_options: Optional[dict[str, Any]] = None
        self._ready_http_url: Optional[str] = None
        self._udp_url: Optional[str] = None
        self._live_hls_dir: Optional[Path] = None
        self._live_hls_process: Optional[Any] = None
        self._http_ts_to_hls: bool = False

    def start(
        self,
        source_url: str,
        output_format: str = "http_ts",
        input_format: Optional[str] = None,
        backend_name: Optional[str] = None,
        backend_options: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Запустить сессию. Вернуть путь для плеера.
        output_format: "http_ts" | "hls" | "webrtc" из настроек.
        input_format: результат get_input_format(url); если не передан — вычисляется.
        backend_name, backend_options: результат get_backend_for_link и опции; сохраняются для GET live.
        """
        if not source_url or not isinstance(source_url, str):
            raise ValueError("source_url required")
        url = source_url.strip()
        inp = input_format if input_format is not None else get_input_format(url)
        if inp is None:
            raise ValueError("Unsupported URL scheme. Got: " + url[:80])

        self._session_id = str(uuid.uuid4())[:8]
        self._source_url = url
        self._input_format = inp
        self._output_format = "webrtc" if output_format == "webrtc" else ("hls" if output_format == "hls" else "http_ts")
        self._backend_name = backend_name
        self._backend_options = backend_options or {}

        if inp == "http":
            self._ready_http_url = url
            if self._output_format == "hls" and not url.lower().split("?")[0].endswith(".m3u8"):
                self._http_ts_to_hls = True
                return f"/api/streams/live/{self._session_id}"
            return f"/api/streams/proxy/{self._session_id}/"

        if inp == "udp":
            self._udp_url = url

        # udp, rtp, rtsp, srt, hls, tcp, file — всегда live
        return f"/api/streams/live/{self._session_id}"

    def stop(self) -> None:
        """Остановить сессию и процесс HLS (если был)."""
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
        self._http_ts_to_hls = False
        self._session_id = None
        self._source_url = None
        self._input_format = None
        self._backend_name = None
        self._backend_options = None
        self._ready_http_url = None
        self._udp_url = None

    def is_alive(self) -> bool:
        """Активна ли сессия (до stop())."""
        return self._session_id is not None

    def get_source_url(self) -> Optional[str]:
        """URL источника для передачи в бэкенд (stream/start_hls)."""
        return self._source_url

    def get_input_format(self) -> Optional[str]:
        """Входной формат сессии (udp, http, rtp, rtsp, …)."""
        return self._input_format

    def get_backend_name(self) -> Optional[str]:
        """Имя бэкенда, выбранного для этой сессии."""
        return self._backend_name

    def get_backend_options(self) -> dict:
        """Опции бэкенда для stream/start_hls."""
        return self._backend_options or {}

    def get_udp_url(self) -> Optional[str]:
        return self._udp_url

    def get_http_url(self) -> Optional[str]:
        return self._ready_http_url

    def get_http_base_url(self) -> Optional[str]:
        """Базовый URL для HTTP (для прокси сегментов HLS)."""
        if not self._ready_http_url:
            return None
        parts = self._ready_http_url.rsplit("/", 1)
        return (parts[0] + "/") if len(parts) == 2 else (self._ready_http_url + "/")

    def get_session_dir(self) -> Optional[Path]:
        """Каталог сессии (для раздачи HLS сегментов)."""
        if self._live_hls_dir is not None:
            return self._live_hls_dir
        return None

    def get_playlist_path(self) -> Optional[Path]:
        """Путь к playlist.m3u8 на диске (UDP+HLS)."""
        if self._live_hls_dir is not None:
            return self._live_hls_dir / "playlist.m3u8"
        return None

    def set_live_hls(self, session_dir: Path, process: Any) -> None:
        """Задать каталог и процесс для UDP→HLS."""
        self._live_hls_dir = session_dir
        self._live_hls_process = process

    def get_playback_type(self) -> str:
        """Тип воспроизведения для ответа API: http_proxy | http_hls | udp_ts | udp_hls | webrtc."""
        if self._output_format == "webrtc":
            return "webrtc"
        if self._ready_http_url:
            if self._http_ts_to_hls or (self._output_format == "hls" and self._ready_http_url.lower().split("?")[0].endswith(".m3u8")):
                return "http_hls"
            return "http_proxy"
        if self._udp_url or self._source_url:
            return "udp_hls" if self._output_format == "hls" else "udp_ts"
        return "http_proxy"

    def get_use_mpegts_js(self) -> bool:
        """Нужен mpegts.js на фронте (для HTTP TS и UDP TS)."""
        if self._ready_http_url:
            if self._http_ts_to_hls:
                return False
            return self._output_format != "hls" or not self._ready_http_url.lower().endswith(".m3u8")
        if self._udp_url:
            return self._output_format != "hls"
        return True

    def get_use_native_video(self) -> bool:
        """Нативный <video> для HLS (обычно false — используем hls.js)."""
        return False
