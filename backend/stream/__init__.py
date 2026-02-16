"""Модуль скриншотов и просмотра потоков (UDP/HTTP). Без зависимости от Astra."""
from backend.stream.capture import StreamFrameCapture
from backend.stream.playback import StreamPlaybackSession

__all__ = ["StreamFrameCapture", "StreamPlaybackSession"]
