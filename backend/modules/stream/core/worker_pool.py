from __future__ import annotations

import asyncio
import uuid
from typing import Any, Optional

from backend.modules.stream.core.pipeline import Pipeline
from backend.modules.stream.core.types import StreamResult, StreamTask


class WorkerPool:
    """Простой asyncio пул: очередь задач, воркеры, хранение результатов в памяти."""

    def __init__(
        self,
        pipeline: Pipeline | None = None,
        *,
        max_workers: int = 2,
        queue_maxsize: int = 100,
    ):
        self._pipeline = pipeline or Pipeline()
        self._queue: asyncio.Queue[StreamTask] = asyncio.Queue(queue_maxsize)
        self._events: dict[str, asyncio.Event] = {}
        self._results: dict[str, StreamResult] = {}
        self._workers = [asyncio.create_task(self._worker_loop(), name=f"stream-worker-{i}") for i in range(max_workers)]

    async def _worker_loop(self) -> None:
        while True:
            task = await self._queue.get()
            try:
                result = await self._pipeline.process(task)
                self._results[task.id] = result
            except Exception as exc:  # pragma: no cover - защитный блок
                self._results[task.id] = StreamResult(
                    success=False,
                    output_path=None,
                    error_code="EXCEPTION",
                    error_message=str(exc),
                    metrics={},
                    backend_name=None,
                )
            finally:
                ev = self._events.get(task.id)
                if ev:
                    ev.set()
                self._queue.task_done()

    async def submit(self, task: StreamTask, *, timeout: float = 5.0) -> str:
        if not task.id:
            task.id = str(uuid.uuid4())
        ev = asyncio.Event()
        self._events[task.id] = ev
        await asyncio.wait_for(self._queue.put(task), timeout=timeout)
        return task.id

    async def get_result(self, task_id: str, *, timeout: Optional[float] = None) -> Optional[StreamResult]:
        ev = self._events.get(task_id)
        if not ev:
            return None
        try:
            await asyncio.wait_for(ev.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        return self._results.get(task_id)

    async def shutdown(self) -> None:
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)


_default_pool: WorkerPool | None = None


def get_pool() -> WorkerPool:
    global _default_pool
    if _default_pool is None:
        _default_pool = WorkerPool()
    return _default_pool
