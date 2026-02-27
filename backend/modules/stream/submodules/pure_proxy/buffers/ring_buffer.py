from __future__ import annotations

import threading
from collections import deque
from typing import Optional


class RingBuffer:
    """Простой потокобезопасный кольцевой буфер для bytes.

    Не для больших объёмов (используется для stub UDP→HTTP прокси).
    """

    def __init__(self, max_chunks: int = 128):
        self._buf: deque[bytes] = deque(maxlen=max_chunks)
        self._lock = threading.Lock()

    def push(self, chunk: bytes) -> None:
        with self._lock:
            self._buf.append(chunk)

    def read_all(self) -> bytes:
        with self._lock:
            data = b"".join(self._buf)
            self._buf.clear()
            return data

    def snapshot(self) -> list[bytes]:
        with self._lock:
            return list(self._buf)
