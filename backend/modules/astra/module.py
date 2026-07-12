import asyncio
import logging
import time
from typing import Any

from backend.modules.base import BaseModule
from backend.core.config import load_instances
from backend.core.plugin.registry import get_module_settings
from .services import AstraClient

_log = logging.getLogger("nms.astra.module")


class AstraModule(BaseModule):
    """Класс жизненного цикла модуля Astra."""

    def __init__(self, context):
        super().__init__(context)
        self.cache: dict[str, dict[str, Any]] = {}
        self.history: dict[str, list[dict[str, Any]]] = {}
        self._running = False
        self._poll_task: asyncio.Task | None = None

    def init(self) -> None:
        """Подготовка модуля."""
        _log.info("Инициализация модуля Astra...")

    def start(self) -> None:
        """Запуск модуля и фоновой задачи мониторинга."""
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        _log.info("Модуль Astra успешно запущен.")

    async def stop(self) -> None:
        """Остановка фоновой задачи."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
        _log.info("Модуль Astra остановлен.")

    def get_status(self) -> dict[str, Any]:
        """Получить статус модуля."""
        instances = load_instances()
        online_count = sum(
            1
            for k, v in self.cache.items()
            if v.get("online")
        )
        return {
            "status": "running" if self._running else "stopped",
            "instances_total": len(instances),
            "instances_online": online_count,
        }

    async def _poll_loop(self) -> None:
        """Бесконечный цикл опроса экземпляров Astra."""
        while self._running:
            try:
                settings = get_module_settings("astra") or {}
                ui_interval = int(settings.get("ui_update_interval", 5))
                query_timeout = float(settings.get("query_timeout", 5.0))
                history_limit = int(settings.get("history_limit", 20))

                instances = load_instances()
                tasks = []
                for cfg in instances:
                    tasks.append(
                        self._poll_instance(cfg, query_timeout, history_limit)
                    )

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Ждем следующей итерации
                await asyncio.sleep(ui_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _log.error("Ошибка в цикле опроса Astra: %s", exc, exc_info=True)
                await asyncio.sleep(5)

    async def _poll_instance(
        self, cfg: Any, timeout: float, history_limit: int
    ) -> None:
        """Опросить один экземпляр Astra."""
        key = f"{cfg.host}:{cfg.port}"
        client = AstraClient(cfg.host, cfg.port, cfg.api_key, timeout=timeout)
        try:
            snapshot = await client.get_snapshot()

            # Сбор CPU и памяти из системного статуса astra-monitor
            system_data = snapshot.get("system") or {}
            cpu_usage = float(system_data.get("cpu_percent", 0.0))
            mem_total = float(system_data.get("mem_total_kb", 1))
            mem_avail = float(system_data.get("mem_available_kb", 0))
            server_mem_usage = (
                round((mem_total - mem_avail) / mem_total * 100.0, 1)
                if mem_total > 0
                else 0.0
            )
            # astra-rss
            astra_rss = float(system_data.get("astra_rss_kb", 0))

            # Добавляем точку в историю
            if key not in self.history:
                self.history[key] = []

            self.history[key].append(
                {
                    "time": int(time.time()),
                    "cpu": cpu_usage,
                    "server_mem": server_mem_usage,
                    "astra_rss": astra_rss,
                }
            )

            # Ограничиваем историю
            if len(self.history[key]) > history_limit:
                self.history[key] = self.history[key][-history_limit:]

            self.cache[key] = {
                "online": True,
                "last_seen": int(time.time()),
                "snapshot": snapshot,
                "error": None,
            }
        except Exception as exc:
            # В случае сбоя обновляем флаг доступности, но сохраняем последний снимок
            self.cache[key] = {
                "online": False,
                "last_seen": self.cache.get(key, {}).get("last_seen", 0),
                "snapshot": self.cache.get(key, {}).get("snapshot"),
                "error": str(exc),
            }
            # Добавим и для истории сбойную точку с нулями, чтобы графики не ломались
            if key not in self.history:
                self.history[key] = []
            self.history[key].append(
                {
                    "time": int(time.time()),
                    "cpu": 0.0,
                    "server_mem": 0.0,
                    "astra_rss": 0.0,
                }
            )
            if len(self.history[key]) > history_limit:
                self.history[key] = self.history[key][-history_limit:]
