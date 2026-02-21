"""Stream analysis via ffprobe: codecs, resolution, duration."""
from __future__ import annotations

import json
import subprocess
from typing import Any, Optional

from backend.utils import find_executable


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
