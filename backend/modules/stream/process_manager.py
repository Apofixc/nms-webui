"""Process/session manager for stream playback workers."""
from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any


@dataclass
class StreamWorker:
    session_id: str
    source_url: str | None
    backend: str | None
    output_format: str | None
    created_at: float
    restarts: int = 0
    last_error: str | None = None


class StreamProcessManager:
    def __init__(self, max_restarts: int = 1):
        self._workers: dict[str, StreamWorker] = {}
        self._max_restarts = max_restarts

    def register(self, session_id: str, *, source_url: str | None, backend: str | None, output_format: str | None) -> None:
        self._workers[session_id] = StreamWorker(
            session_id=session_id,
            source_url=source_url,
            backend=backend,
            output_format=output_format,
            created_at=time(),
        )

    def unregister(self, session_id: str) -> None:
        self._workers.pop(session_id, None)

    def mark_failed(self, session_id: str, error: str) -> bool:
        worker = self._workers.get(session_id)
        if worker is None:
            return False
        worker.last_error = error
        if worker.restarts >= self._max_restarts:
            return False
        worker.restarts += 1
        return True

    def status(self) -> dict[str, Any]:
        return {
            "workers": [
                {
                    "session_id": w.session_id,
                    "source_url": w.source_url,
                    "backend": w.backend,
                    "output_format": w.output_format,
                    "created_at": w.created_at,
                    "restarts": w.restarts,
                    "last_error": w.last_error,
                }
                for w in self._workers.values()
            ],
            "count": len(self._workers),
        }


_MANAGER = StreamProcessManager()


def get_stream_process_manager() -> StreamProcessManager:
    return _MANAGER
