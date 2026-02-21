"""WebRTC/WHEP stream backend. Stub until full implementation."""
from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from backend.stream.backends.base import StreamBackend


class WebRTCStreamBackend(StreamBackend):
    name = "webrtc"
    input_types: set[str] = set()
    output_types = {"webrtc"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        return False

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        if False:
            yield b""
