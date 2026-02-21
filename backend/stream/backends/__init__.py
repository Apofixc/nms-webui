"""Stream backends: FFmpeg, VLC, GStreamer, Astra, TSDuck, UDP proxy, WebRTC."""
from backend.stream.backends.astra import AstraStreamBackend
from backend.stream.backends.base import StreamBackend
from backend.stream.backends.ffmpeg import FFmpegStreamBackend
from backend.stream.backends.gstreamer import GStreamerStreamBackend
from backend.stream.backends.tsduck import TSDuckStreamBackend
from backend.stream.backends.udp_to_http import ProxyUdpStreamBackend
from backend.stream.backends.vlc import VLCStreamBackend
from backend.stream.backends.webrtc import WebRTCStreamBackend

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
