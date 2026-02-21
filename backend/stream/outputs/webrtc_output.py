"""WHEP (WebRTC HTTP Egress Protocol) endpoint helpers: SDP exchange and optional aiortc."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

WHEP_AVAILABLE = False
_whep_error: Optional[str] = None

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription
    WHEP_AVAILABLE = True
except ImportError as e:
    _whep_error = str(e)


def is_whep_available() -> bool:
    """Return True if aiortc is installed and WHEP can be used."""
    return WHEP_AVAILABLE


def whep_unavailable_message() -> str:
    """Message to show when WHEP is not available (e.g. aiortc not installed)."""
    install_hint = " Install with: pip install aiortc"
    alt_hint = " Alternatively, use HLS or HTTP-TS output in Stream settings."
    if _whep_error:
        return f"WebRTC (WHEP) requires aiortc: {_whep_error}.{install_hint}{alt_hint}"
    return f"WebRTC (WHEP) is not available.{alt_hint}"


async def whep_handle_offer(sdp_offer: str) -> Tuple[str, Optional[object]]:
    """
    Handle WHEP SDP offer: create RTCPeerConnection, set remote description, create answer.
    Returns (sdp_answer, pc). Caller must call whep_close(pc) on disconnect/DELETE.
    """
    if not WHEP_AVAILABLE:
        logger.warning("WHEP requested but aiortc not available: %s", whep_unavailable_message())
        raise RuntimeError(whep_unavailable_message())
    from aiortc import RTCPeerConnection, RTCSessionDescription

    pc = RTCPeerConnection()
    try:
        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp_offer, type="offer"))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        sdp = pc.localDescription.sdp if pc.localDescription else ""
        logger.info("WHEP offer handled successfully")
        return (sdp, pc)
    except Exception:
        logger.exception("WHEP offer failed")
        await pc.close()
        raise


async def whep_close(pc: object) -> None:
    """Close WHEP peer connection. Safe to call with None."""
    if pc is None:
        return
    try:
        close_fn = getattr(pc, "close", None)
        if close_fn and callable(close_fn):
            result = close_fn()
            if hasattr(result, "__await__"):
                await result
    except Exception:
        pass


__all__ = [
    "WHEP_AVAILABLE",
    "is_whep_available",
    "whep_unavailable_message",
    "whep_handle_offer",
    "whep_close",
]
