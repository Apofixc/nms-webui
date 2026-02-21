"""WebRTC/WHEP stream backend. WHEP endpoint in main; this backend marks webrtc output as supported when aiortc is available."""
from __future__ import annotations

from typing import Any, AsyncGenerator, Optional

from backend.stream.backends.base import StreamBackend


class WebRTCStreamBackend(StreamBackend):
    name = "webrtc"
    input_types = {"udp_ts", "http", "file", "rtp", "tcp", "rtsp", "srt", "hls"}
    output_types = {"webrtc"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        # Always True so playback session can start and return WHEP URL; POST /whep returns 503 if aiortc missing.
        return True

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[bytes, None]:
        # Media is delivered via WHEP (POST SDP at /api/streams/whep/{session_id}), not via HTTP-TS stream.
        yield b""
