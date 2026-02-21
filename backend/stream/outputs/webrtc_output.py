"""WHEP (WebRTC HTTP Egress Protocol) endpoint helpers: SDP exchange and optional aiortc."""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

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


def _media_player_for_url(source_url: str) -> Any:
    """Create aiortc MediaPlayer for stream URL (HTTP/UDP/RTSP etc.). Returns (player, None) or (None, error)."""
    try:
        from aiortc.contrib.media import MediaPlayer
    except ImportError:
        return None, "aiortc.contrib.media not available"
    if not source_url or not source_url.strip():
        return None, "empty source URL"
    url = source_url.strip()
    fmt = None
    if url.lower().startswith("udp://") or url.lower().startswith("udp@"):
        fmt = "mpegts"
    opts = {}
    try:
        player = MediaPlayer(url, format=fmt, options=opts, timeout=10)
        if player.video is None and player.audio is None:
            return None, "no video or audio in stream"
        return player, None
    except Exception as e:
        logger.exception("MediaPlayer failed for %s", url[:80])
        return None, str(e)


async def whep_handle_offer(
    sdp_offer: str,
    source_url: Optional[str] = None,
) -> Tuple[str, Any, Optional[Any]]:
    """
    Handle WHEP SDP offer: create RTCPeerConnection, optionally add media from source_url, create answer.
    Returns (sdp_answer, pc, player). Caller must call whep_close(pc, player) on disconnect/DELETE.
    If source_url is set, uses aiortc MediaPlayer (FFmpeg) to feed video/audio into the connection.
    """
    if not WHEP_AVAILABLE:
        logger.warning("WHEP requested but aiortc not available: %s", whep_unavailable_message())
        raise RuntimeError(whep_unavailable_message())
    from aiortc import RTCPeerConnection, RTCSessionDescription

    pc = RTCPeerConnection()
    player: Optional[Any] = None
    try:
        if source_url:
            player, err = _media_player_for_url(source_url)
            if player is not None:
                if player.video:
                    pc.addTrack(player.video)
                if player.audio:
                    pc.addTrack(player.audio)
                logger.info("WHEP media source attached: %s", source_url[:80])
            else:
                logger.warning("WHEP no media source (%s), stream may be black: %s", err, source_url[:80])

        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp_offer, type="offer"))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        sdp = pc.localDescription.sdp if pc.localDescription else ""
        logger.info("WHEP offer handled successfully")
        return (sdp, pc, player)
    except Exception:
        logger.exception("WHEP offer failed")
        if player is not None:
            for track in (player.video, player.audio):
                if track is not None and hasattr(track, "stop"):
                    try:
                        track.stop()
                    except Exception:
                        pass
        await pc.close()
        raise


async def whep_close(pc: object, player: Optional[object] = None) -> None:
    """
    Close WHEP peer connection and optional media player.
    Order: close PC first, then stop player tracks (avoids aiortc hang).
    """
    if pc is not None:
        try:
            close_fn = getattr(pc, "close", None)
            if close_fn and callable(close_fn):
                result = close_fn()
                if hasattr(result, "__await__"):
                    await result
        except Exception:
            pass
    if player is not None:
        try:
            for attr in ("video", "audio"):
                track = getattr(player, attr, None)
                if track is not None and hasattr(track, "stop"):
                    try:
                        track.stop()
                    except Exception:
                        pass
        except Exception:
            pass


__all__ = [
    "WHEP_AVAILABLE",
    "is_whep_available",
    "whep_unavailable_message",
    "whep_handle_offer",
    "whep_close",
]
