"""Stream analysis via ffprobe and input format detection from URL."""
from __future__ import annotations

import json
import subprocess
from typing import Any, Optional

from backend.core.utils import find_executable

# Единый список входных форматов для реестра и конвертера
INPUT_FORMATS = ("udp", "http", "rtp", "file", "rtsp", "srt", "hls", "tcp")


def _is_udp_url(url: str) -> bool:
    return isinstance(url, str) and url.strip().lower().startswith("udp://")


def _is_http_url(url: str) -> bool:
    return isinstance(url, str) and (
        url.startswith("http://") or url.startswith("https://")
    )


def get_input_format_from_url(url: str) -> Optional[str]:
    """
    Определить входной формат по URL для выбора связки в реестре.
    Возвращает одно из: udp, http, rtp, rtsp, srt, hls, tcp, file или None.
    """
    if not url or not isinstance(url, str):
        return None
    u = url.strip().lower()
    if _is_udp_url(url.strip()):
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
    if _is_http_url(url.strip()):
        if ".m3u8" in url.split("?")[0]:
            return "hls"
        return "http"
    return None


def probe_url(
    url: str,
    ffprobe_bin: str = "ffprobe",
    timeout_sec: float = 10.0,
    extra_args: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Run ffprobe on URL (HTTP/UDP/file). Returns parsed JSON with streams and format.
    Raises subprocess.CalledProcessError or FileNotFoundError on failure.
    """
    bin_path = find_executable(ffprobe_bin)
    if not bin_path:
        raise FileNotFoundError(f"ffprobe not found: {ffprobe_bin}")
    cmd = [
        bin_path,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-protocol_whitelist", "file,http,https,tcp,tls,udp",
    ]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(url)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=True,
    )
    return json.loads(result.stdout)
