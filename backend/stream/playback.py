"""Сессия просмотра потока в браузере: HTTP → прокси, UDP → live (TS или HLS через main)."""
from __future__ import annotations

import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

from backend.stream.udp_to_http import is_udp_url

__all__ = ["StreamPlaybackSession", "is_http_url", "is_udp_url", "get_input_format"]


def is_http_url(url: str) -> bool:
    """Проверка, что URL — HTTP или HTTPS."""
    return isinstance(url, str) and (
        url.startswith("http://") or url.startswith("https://")
    )


def get_input_format(url: str) -> str | None:
    """
    Определить входной формат по URL для выбора связки в реестре.
    Возвращает "udp", "http" или None, если формат не поддерживается.
    """
    if not url or not isinstance(url, str):
        return None
    u = url.strip()
    if is_udp_url(u):
        return "udp"
    if is_http_url(u):
        return "http"
    return None


class StreamPlaybackSession:
    """
    Сессия просмотра потока.
    Две ветки по формату вывода (http_ts | hls):
    - Вывод HTTP (http_ts): источник HTTP → прокси; UDP → live (main стримит TS через бэкенды).
    - Вывод HLS: источник уже HLS (.m3u8) → прокси; UDP/HTTP TS → main конвертирует в HLS (start_hls).
    """

    def __init__(self, output_base_dir: Optional[Path] = None):
        self._output_base = output_base_dir or Path(tempfile.gettempdir()) / "nms_streams"
        self._output_base.mkdir(parents=True, exist_ok=True)
        self._session_id: Optional[str] = None
        self._ready_http_url: Optional[str] = None
        self._udp_url: Optional[str] = None
        self._output_format: str = "http_ts"
        self._live_hls_dir: Optional[Path] = None
        self._live_hls_process: Optional[Any] = None
        self._http_ts_to_hls: bool = False

    def start(self, source_url: str, output_format: str = "http_ts") -> str:
        """
        Запустить сессию. Вернуть путь для плеера.
        output_format: "http_ts" | "hls" из настроек (формат вывода).
        Только HTTP и UDP; иначе RuntimeError.
        """
        if not source_url or not isinstance(source_url, str):
            raise ValueError("source_url required")
        url = source_url.strip()
        self._output_format = "webrtc" if output_format == "webrtc" else ("hls" if output_format == "hls" else "http_ts")
        self._session_id = str(uuid.uuid4())[:8]

        if is_http_url(url):
            self._ready_http_url = url
            if self._output_format == "hls" and not url.lower().endswith(".m3u8"):
                self._http_ts_to_hls = True
                return f"/api/streams/live/{self._session_id}"
            return f"/api/streams/proxy/{self._session_id}/"

        if is_udp_url(url):
            self._udp_url = url
            return f"/api/streams/live/{self._session_id}"

        raise RuntimeError("Only HTTP and UDP URLs are supported. Got: " + url[:50])

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
        self._ready_http_url = None
        self._udp_url = None

    def is_alive(self) -> bool:
        """Активна ли сессия (до stop())."""
        return self._session_id is not None

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
        """Тип воспроизведения для ответа API: http_proxy | http_hls | udp_ts | udp_hls."""
        if self._ready_http_url:
            if self._http_ts_to_hls or (self._output_format == "hls" and self._ready_http_url.lower().endswith(".m3u8")):
                return "http_hls"
            return "http_proxy"
        if self._udp_url:
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
