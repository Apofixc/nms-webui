"""Класс модуля Astra — жизненный цикл."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.modules.base import BaseModule
from backend.modules.astra.services.health_checker import run_loop

_log = logging.getLogger("nms.module.astra")


class AstraModule(BaseModule):
    def __init__(self, context):
        super().__init__(context)
        self._health_task: asyncio.Task | None = None

    def init(self) -> None:
        _log.info("Astra module initialized (id=%s)", self.context.module_id)

    def start(self) -> None:
        try:
            loop = asyncio.get_event_loop()
            self._health_task = loop.create_task(run_loop())
            _log.info("Astra health checker started")
        except RuntimeError:
            _log.warning("No event loop — health checker not started (will work in request mode)")

    def stop(self) -> None:
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
            _log.info("Astra health checker stopped")

    def get_status(self) -> dict[str, Any]:
        from backend.modules.astra.services.health_checker import get_status
        status = get_status()
        return {
            "module": "astra",
            "running": self._health_task is not None and not self._health_task.done(),
            "instances_count": len(status.get("instances", [])),
            "events_count": len(status.get("events", [])),
        }
