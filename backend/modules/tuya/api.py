"""API маршруты модуля управления устройствами Tuya."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.plugin.registry import get_instance
from backend.modules.tuya.storage import TuyaDeviceSchema

from backend.modules.tuya.widgets import widget_router

router = APIRouter(prefix="/api/v1/m/tuya", tags=["tuya"])
router.include_router(widget_router)


def get_router(ctx: Any = None) -> APIRouter:
    """Фабричная функция возврата API роутера модуля."""
    return router



class AddDeviceRequest(BaseModel):
    """Схема запроса добавления нового устройства."""

    device_id: str
    name: str = ""
    ip: str | None = None
    local_key: str | None = None
    protocol_version: str = "3.3"
    category: str = "general"
    mode: str = "auto"


class CommandRequest(BaseModel):
    """Схема отправки команды устройству."""

    commands: list[dict[str, Any]] | dict[str, Any] = Field(
        ...,
        description="Список команд [{'code': 'switch_1', 'value': True}] или словарь {'1': True}",
    )
    mode: str | None = Field(default=None, description="Опциональный выбор метода: auto, local, cloud")


def _get_tuya_module() -> Any:
    instance = get_instance("tuya")
    if not instance:
        raise HTTPException(status_code=503, detail="Модуль Tuya не активен или не инициализирован")
    return instance


@router.get("/status")
async def get_status():
    """Получить текущий статус и метрики модуля Tuya."""
    module = _get_tuya_module()
    return module.get_status()


@router.get("/devices", response_model=list[TuyaDeviceSchema])
async def list_devices():
    """Получить список всех устройств Tuya."""
    module = _get_tuya_module()
    if not module.storage:
        return []
    return module.storage.get_all()


@router.post("/devices", response_model=TuyaDeviceSchema)
async def add_device(req: AddDeviceRequest):
    """Добавить или зарегистрировать устройство Tuya."""
    module = _get_tuya_module()
    if not module.storage:
        raise HTTPException(status_code=500, detail="Хранилище модуля недоступно")

    device = TuyaDeviceSchema(
        device_id=req.device_id.strip(),
        name=req.name.strip() or req.device_id,
        ip=req.ip.strip() if req.ip else None,
        local_key=req.local_key.strip() if req.local_key else None,
        protocol_version=req.protocol_version,
        category=req.category,
        mode=req.mode,
    )
    return module.storage.upsert(device)


@router.get("/devices/{device_id}", response_model=TuyaDeviceSchema)
async def get_device(device_id: str):
    """Получить детальную информацию по конкретному устройству."""
    module = _get_tuya_module()
    if not module.storage:
        raise HTTPException(status_code=500, detail="Хранилище недоступно")

    dev = module.storage.get(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Устройство {device_id} не найдено")
    return dev


@router.put("/devices/{device_id}", response_model=TuyaDeviceSchema)
async def update_device(device_id: str, req: AddDeviceRequest):
    """Обновить параметры зарегистрированного устройства."""
    module = _get_tuya_module()
    if not module.storage:
        raise HTTPException(status_code=500, detail="Хранилище недоступно")

    existing = module.storage.get(device_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Устройство {device_id} не найдено")

    existing.name = req.name.strip() if req.name else existing.name
    existing.ip = req.ip.strip() if req.ip else existing.ip
    existing.local_key = req.local_key.strip() if req.local_key else existing.local_key
    existing.protocol_version = req.protocol_version or existing.protocol_version
    existing.category = req.category or existing.category
    existing.mode = req.mode or existing.mode

    return module.storage.upsert(existing)


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str):
    """Удалить устройство из управления."""
    module = _get_tuya_module()
    if not module.storage:
        raise HTTPException(status_code=500, detail="Хранилище недоступно")

    deleted = module.storage.delete(device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Устройство {device_id} не найдено")
    return {"status": "success", "message": f"Устройство {device_id} удалено"}


@router.post("/devices/{device_id}/command")
async def send_command(device_id: str, req: CommandRequest):
    """Отправить команду управления на устройство (включение/выключение, DPS)."""
    module = _get_tuya_module()
    if not module.storage or not module.controller:
        raise HTTPException(status_code=500, detail="Контроллер модуля недоступен")

    dev = module.storage.get(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Устройство {device_id} не найдено")

    target_mode = req.mode or dev.mode or "auto"
    success = await module.controller.send_command(
        device_id=dev.device_id,
        commands=req.commands,
        mode=target_mode,
        ip=dev.ip,
        local_key=dev.local_key,
        protocol_version=dev.protocol_version,
    )

    if not success:
        raise HTTPException(status_code=502, detail="Не удалось отправить команду устройству Tuya")

    return {"status": "success", "device_id": device_id, "mode_used": target_mode}


@router.post("/sync")
async def sync_cloud_devices():
    """Синхронизировать данные устройств через Tuya Cloud API."""
    module = _get_tuya_module()
    if not module.cloud_client:
        raise HTTPException(status_code=400, detail="Tuya Cloud API credentials не настроены")

    if not module.storage:
        raise HTTPException(status_code=500, detail="Хранилище недоступно")

    devices = module.storage.get_all()
    synced_count = 0
    for dev in devices:
        status_list = await module.cloud_client.get_device_status(dev.device_id)
        if status_list is not None:
            dps_map = {item.get("code"): item.get("value") for item in status_list if "code" in item}
            module.storage.update_status(dev.device_id, online=True, dps=dps_map)
            synced_count += 1

    return {"status": "success", "synced_devices": synced_count}
