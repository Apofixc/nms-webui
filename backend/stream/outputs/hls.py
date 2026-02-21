"""Параметры и пути для HLS: нормализация hls_time/hls_list_size, шаблоны имён сегментов и playlist."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def norm_hls_params(opts: dict[str, Any]) -> tuple[int, int]:
    """
    Нормализовать hls_time и hls_list_size из словаря опций (например opts["ffmpeg"] или opts["vlc"]).
    Возвращает (hls_time, hls_list_size).
    """
    hls_time = 2
    if isinstance(opts.get("hls_time"), (int, float)):
        hls_time = max(1, min(30, int(opts["hls_time"])))
    hls_list_size = 5
    if isinstance(opts.get("hls_list_size"), (int, float)):
        hls_list_size = max(2, min(30, int(opts["hls_list_size"])))
    return hls_time, hls_list_size


def default_playlist_path(session_dir: Path) -> Path:
    """Стандартный путь к playlist.m3u8."""
    return session_dir / "playlist.m3u8"


def ffmpeg_segment_pattern(session_dir: Path) -> str:
    """Шаблон имён сегментов для FFmpeg (-hls_segment_filename)."""
    return str(session_dir / "seg_%03d.ts")


def vlc_segment_pattern(session_dir: Path) -> str:
    """Шаблон имён сегментов для VLC (livehttp index-url)."""
    return str(session_dir / "seg_###.ts")


def gstreamer_segment_path(session_dir: Path) -> Path:
    """Путь к шаблону сегментов для GStreamer hlssink2."""
    return session_dir / "seg_%05d.ts"


def tsduck_segment_path(session_dir: Path) -> Path:
    """Путь к единственному сегменту для TSDuck (-O hls)."""
    return session_dir / "seg.ts"
