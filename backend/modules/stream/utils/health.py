"""Health-check for running processes and HLS liveness."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


def is_process_alive(proc: Any, timeout: float | None = None) -> bool:
    """
    Return True if the process is still running.
    proc: subprocess.Popen or object with .poll() method.
    timeout: unused, for future use (e.g. consider stale after timeout).
    """
    if proc is None:
        return False
    poll = getattr(proc, "poll", None)
    if poll is None:
        return False
    return poll() is None


def hls_playlist_ready(session_dir: Path) -> bool:
    """
    Return True if HLS playlist exists and has at least one segment file.
    Used to avoid 502 while waiting for first segments.
    """
    if not session_dir or not session_dir.is_dir():
        return False
    pl = session_dir / "playlist.m3u8"
    if not pl.exists() or pl.stat().st_size == 0:
        return False
    for pattern in ("seg_*.ts", "seg-*.ts", "segment*.ts"):
        if list(session_dir.glob(pattern)):
            return True
    return False


async def wait_for_hls_playlist(
    session_dir: Path,
    timeout_sec: float = 10.0,
    check_interval: float = 0.2,
) -> bool:
    """
    Wait until HLS playlist and at least one segment appear, or timeout.
    Returns True if ready, False on timeout.
    """
    deadline = asyncio.get_running_loop().time() + timeout_sec
    while asyncio.get_running_loop().time() < deadline:
        if hls_playlist_ready(session_dir):
            return True
        await asyncio.sleep(check_interval)
    return False
