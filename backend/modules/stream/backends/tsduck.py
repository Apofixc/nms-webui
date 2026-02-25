"""TSDuck stream backend."""
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.stream.backends.base import StreamBackend


class TSDuckStreamBackend(StreamBackend):
    """TSDuck streaming backend using tsp command."""

    name = "tsduck"
    display_name = "TSDuck"
    description = "TSDuck MPEG Transport Stream Toolkit"
    
    input_types = {"udp", "udp_ts", "http", "rtp", "file", "rtsp", "srt", "hls", "tcp"}
    output_types = {"http_ts", "http_hls"}

    @classmethod
    def available(cls, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if TSDuck (tsp) is available."""
        try:
            result = subprocess.run(
                ["tsp", "--version"],
                capture_output=True,
                timeout=5,
                text=True,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False

    def __init__(self, options: Optional[Dict[str, Any]] = None):
        self.options = options or {}
        self.tsp_bin = "tsp"
        if isinstance(self.options.get("bin"), str):
            self.tsp_bin = self.options["bin"].strip()

    def _build_input_args(self, input_url: str, input_type: str) -> List[str]:
        """Build input arguments for TSDuck."""
        if input_type in {"udp", "udp_ts"}:
            return ["-I", "ip", input_url]
        elif input_type == "http":
            return ["-I", "http", input_url]
        elif input_type == "rtp":
            return ["-I", "ip", input_url]
        elif input_type == "file":
            return ["-I", "file", input_url]
        elif input_type == "rtsp":
            return ["-I", "rtsp", input_url]
        elif input_type == "srt":
            return ["-I", "srt", input_url]
        elif input_type == "hls":
            return ["-I", "hls", input_url]
        elif input_type == "tcp":
            return ["-I", "ip", input_url]
        else:
            raise ValueError(f"Unsupported input type: {input_type}")

    def _build_output_args(self, output_url: str, output_type: str) -> List[str]:
        """Build output arguments for TSDuck."""
        if output_type == "http_ts":
            # Extract host and port from URL like http://host:port/
            match = re.match(r"http://([^:/]+):(\d+)/?", output_url)
            if not match:
                raise ValueError(f"Invalid HTTP TS output URL: {output_url}")
            host, port = match.groups()
            return ["-O", "http", host, port]
        elif output_type == "http_hls":
            # Extract host and port from URL like http://host:port/stream.m3u8
            match = re.match(r"http://([^:/]+):(\d+)/", output_url)
            if not match:
                raise ValueError(f"Invalid HLS output URL: {output_url}")
            host, port = match.groups()
            return ["-O", "hls", host, port]
        else:
            raise ValueError(f"Unsupported output type: {output_type}")

    def build_command(
        self,
        input_url: str,
        input_type: str,
        output_url: str,
        output_type: str,
        extra_args: Optional[List[str]] = None,
    ) -> Tuple[List[str], Dict[str, str]]:
        """Build TSDuck command for streaming."""
        cmd = [self.tsp_bin]
        
        # Input
        cmd.extend(self._build_input_args(input_url, input_type))
        
        # Output
        cmd.extend(self._build_output_args(output_url, output_type))
        
        # Additional arguments
        if extra_args:
            cmd.extend(extra_args)
        
        # Environment variables
        env = os.environ.copy()
        
        return cmd, env

    def get_process_info(self) -> Dict[str, Any]:
        """Get TSDuck process information."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self._get_version(),
            "available": self.available(),
        }

    def _get_version(self) -> str:
        """Get TSDuck version."""
        try:
            result = subprocess.run(
                [self.tsp_bin, "--version"],
                capture_output=True,
                timeout=5,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return "Unknown"
