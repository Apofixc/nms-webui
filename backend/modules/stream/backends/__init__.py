"""Stream backends: FFmpeg, VLC, GStreamer, Astra, TSDuck, UDP proxy, WebRTC."""
from backend.modules.stream.backends.astra import AstraStreamBackend
from backend.modules.stream.backends.base import StreamBackend
from backend.modules.stream.backends.ffmpeg import FFmpegStreamBackend
from backend.modules.stream.backends.gstreamer import GStreamerStreamBackend
from backend.modules.stream.backends.tsduck import TSDuckStreamBackend
from backend.modules.stream.backends.udp_to_http import ProxyUdpStreamBackend
from backend.modules.stream.backends.vlc import VLCStreamBackend
from backend.modules.stream.backends.webrtc import WebRTCStreamBackend

__all__ = [
    "StreamBackend",
    "FFmpegStreamBackend",
    "VLCStreamBackend",
    "GStreamerStreamBackend",
    "AstraStreamBackend",
    "TSDuckStreamBackend",
    "ProxyUdpStreamBackend",
    "WebRTCStreamBackend",
]
