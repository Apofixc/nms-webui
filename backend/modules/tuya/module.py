"""Основная бизнес-логика и жизненный цикл модуля Tuya."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from backend.core.plugin.registry import get_module_settings
from backend.modules.base import BaseModule
from backend.modules.tuya.client import TuyaCloudClient, TuyaDeviceController
from backend.modules.tuya.storage import TuyaStorage

_log = logging.getLogger("nms.module.tuya.module")


class TuyaModule(BaseModule):
    """Модуль управления смарт-устройствами Tuya."""

    def __init__(self, context: Any):
        super().__init__(context)
        self.storage: TuyaStorage | None = None
        self.cloud_client: TuyaCloudClient | None = None
        self.controller: TuyaDeviceController | None = None
        self._poll_task: asyncio.Task | None = None
        self._running: bool = False

    def _reload_config(self) -> None:
        """Перезагрузка настроек из базы данных."""
        settings = get_module_settings("tuya")
        client_id = settings.get("client_id", "")
        client_secret = settings.get("client_secret", "")
        region = settings.get("region", "eu")

        if client_id and client_secret:
            self.cloud_client = TuyaCloudClient(client_id, client_secret, region)
        else:
            self.cloud_client = None

        self.controller = TuyaDeviceController(self.cloud_client)

    def init(self) -> None:
        """Инициализация ресурсов модуля."""
        _log.info("Инициализация модуля Tuya (id: %s)", self.context.module_id)
        data_dir = self.context.root / "data"
        self.storage = TuyaStorage(data_dir)
        self._reload_config()

    def start(self) -> None:
        """Запуск фоновых процессов модуля."""
        _log.info("Запуск модуля Tuya...")
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._poll_task = loop.create_task(self._poll_loop())
        except RuntimeError:
            _log.warning("Фоновый цикл событий недоступен при start() модуля Tuya")

    async def stop(self) -> None:
        """Остановка модуля Tuya и фоновых задач."""
        _log.info("Остановка модуля Tuya...")
        self._running = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self._poll_task = None

    async def _poll_loop(self) -> None:
        """Фоновый опрос состояния зарегистрированных устройств."""
        while self._running:
            try:
                settings = get_module_settings("tuya")
                poll_interval = int(settings.get("poll_interval_sec", 15))
                self._reload_config()

                if self.storage:
                    devices = self.storage.get_all()
                    for dev in devices:
                        if not self._running:
                            break

                        # Опрос через Cloud если доступен client
                        if self.cloud_client and dev.device_id:
                            status_list = await self.cloud_client.get_device_status(dev.device_id)
                            if status_list is not None:
                                dps_map = {item.get("code"): item.get("value") for item in status_list if "code" in item}
                                self.storage.update_status(dev.device_id, online=True, dps=dps_map)

                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _log.error("Ошибка в фоновом цикле опроса Tuya: %s", exc)
                await asyncio.sleep(10)

    def get_status(self) -> dict[str, Any]:
        """Возврат текущего статуса модуля для системы."""
        devices = self.storage.get_all() if self.storage else []
        total = len(devices)
        online = sum(1 for d in devices if d.online)
        local_count = sum(1 for d in devices if d.ip and d.local_key)

        return {
            "active": self._running,
            "cloud_configured": self.cloud_client is not None,
            "total_devices": total,
            "online_devices": online,
            "local_ready_devices": local_count,
        }
