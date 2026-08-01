"""Хранилище конфигурации и состояния устройств Tuya."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

_log = logging.getLogger("nms.module.tuya.storage")


class TuyaDeviceSchema(BaseModel):
    """Модель смарт-устройства Tuya."""

    device_id: str
    name: str = ""
    ip: str | None = None
    local_key: str | None = None
    protocol_version: str = "3.3"  # 3.1, 3.3, 3.4, 3.5
    category: str = "general"
    online: bool = False
    mode: str = "auto"  # auto, local, cloud
    dps: dict[str, Any] = Field(default_factory=dict)
    updated_at: str | None = None


class TuyaStorage:
    """Управление реестром устройств Tuya и сохранение на диск."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.storage_file = data_dir / "tuya_devices.json"
        self._devices: dict[str, TuyaDeviceSchema] = {}
        self.load()

    def load(self) -> None:
        """Загрузить список устройств из JSON файла."""
        if not self.storage_file.exists():
            self._devices = {}
            return
        try:
            content = self.storage_file.read_text(encoding="utf-8")
            data = json.loads(content)
            if isinstance(data, list):
                self._devices = {item["device_id"]: TuyaDeviceSchema(**item) for item in data if "device_id" in item}
            elif isinstance(data, dict):
                self._devices = {k: TuyaDeviceSchema(**v) for k, v in data.items() if isinstance(v, dict)}
        except Exception as exc:
            _log.warning("Error loading Tuya devices from %s: %s", self.storage_file, exc)
            self._devices = {}

    def save(self) -> None:
        """Сохранить устройства на диск."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            serializable = [dev.model_dump() for dev in self._devices.values()]
            self.storage_file.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            _log.error("Error saving Tuya devices to %s: %s", self.storage_file, exc)

    def get_all(self) -> list[TuyaDeviceSchema]:
        """Возвращает список всех зарегистрированных устройств."""
        return list(self._devices.values())

    def get(self, device_id: str) -> TuyaDeviceSchema | None:
        """Получить устройство по ID."""
        return self._devices.get(device_id)

    def upsert(self, device: TuyaDeviceSchema) -> TuyaDeviceSchema:
        """Добавить или обновить устройство."""
        self._devices[device.device_id] = device
        self.save()
        return device

    def delete(self, device_id: str) -> bool:
        """Удалить устройство."""
        if device_id in self._devices:
            del self._devices[device_id]
            self.save()
            return True
        return False

    def update_status(self, device_id: str, online: bool, dps: dict[str, Any] | None = None) -> None:
        """Обновить онлайн-статус и DPS устройства."""
        dev = self.get(device_id)
        if dev:
            dev.online = online
            if dps is not None:
                dev.dps.update(dps)
            self.upsert(dev)
