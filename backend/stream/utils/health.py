"""Health-check for running processes (e.g. stream/capture subprocesses)."""
from __future__ import annotations

import subprocess
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
