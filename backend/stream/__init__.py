"""Модуль скриншотов, просмотра и анализа потоков (UDP/HTTP). Без зависимости от Astra."""
from backend.stream.capture import StreamFrameCapture
from backend.stream.playback import StreamPlaybackSession
from backend.stream.ts_analyzer import TsAnalyzer

__all__ = ["StreamFrameCapture", "StreamPlaybackSession", "TsAnalyzer"]
