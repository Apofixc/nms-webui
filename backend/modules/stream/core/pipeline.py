"""Конвейер обработки stream: выбор бэкенда, инициализация, выполнение задачи."""
from __future__ import annotations

import asyncio
from typing import Any, Optional, Sequence

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.exceptions import (
    BackendInitializationError,
    BackendProcessError,
)
from backend.modules.stream.core.loader import ModuleLoader, get_loader
from backend.modules.stream.core.router import choose_backend
from backend.modules.stream.core.types import StreamResult, StreamTask


class Pipeline:
    """Простой конвейер: выбирает backend, инициализирует, вызывает process, затем shutdown."""

    def __init__(self, loader: ModuleLoader | None = None):
        self.loader = loader or get_loader()

    async def _run_backend(
        self,
        backend_cls: type[IStreamBackend],
        task: StreamTask,
        config: Optional[dict[str, Any]] = None,
    ) -> StreamResult:
        backend = backend_cls()
        ok = await backend.initialize(config or {})
        if not ok:
            raise BackendInitializationError(f"Backend {backend_cls.__name__} failed to initialize")
        try:
            result = await backend.process(task)
            return result
        except Exception as exc:  # pragma: no cover - оборачиваем
            raise BackendProcessError(str(exc)) from exc
        finally:
            try:
                await backend.shutdown()
            except Exception:
                pass

    async def process(
        self,
        task: StreamTask,
        *,
        required_features: Optional[Sequence[str]] = None,
        backend_config: Optional[dict[str, Any]] = None,
    ) -> StreamResult:
        backend_cls = choose_backend(task, required_features=required_features, loader=self.loader)
        return await self._run_backend(backend_cls, task, backend_config)


# Утилита для синхронных вызовов (legacy API)
def run_task_sync(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    return asyncio.run(coro)


__all__ = ["Pipeline", "run_task_sync"]
