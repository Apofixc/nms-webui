"""API маршруты модуля управления устройствами Tuya."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.core.i18n import make_error_detail, tr
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


def _get_tuya_module(request: Request = None) -> Any:
    instance = get_instance("tuya")
    if not instance:
        raise HTTPException(status_code=503, detail=make_error_detail(request, "TUYA_NOT_ACTIVE", "tuya_not_active"))
    return instance


@router.get("/status")
async def get_status(request: Request = None):
    """Получить текущий статус и метрики модуля Tuya."""
    module = _get_tuya_module(request)
    return module.get_status()


@router.get("/devices", response_model=list[TuyaDeviceSchema])
async def list_devices(request: Request = None):
    """Получить список всех устройств Tuya."""
    module = _get_tuya_module(request)
    if not module.storage:
        return []
    return module.storage.get_all()


@router.post("/devices", response_model=TuyaDeviceSchema)
async def add_device(req: AddDeviceRequest, request: Request = None):
    """Добавить или зарегистрировать устройство Tuya."""
    module = _get_tuya_module(request)
    if not module.storage:
        raise HTTPException(status_code=500, detail=make_error_detail(request, "TUYA_STORAGE_UNAVAILABLE", "tuya_storage_unavailable"))

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
async def get_device(device_id: str, request: Request = None):
    """Получить детальную информацию по конкретному устройству."""
    module = _get_tuya_module(request)
    if not module.storage:
        raise HTTPException(status_code=500, detail=make_error_detail(request, "TUYA_STORAGE_UNAVAILABLE", "tuya_storage_unavailable"))

    dev = module.storage.get(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=make_error_detail(request, "TUYA_DEVICE_NOT_FOUND", "tuya_device_not_found", device_id=device_id))
    return dev


@router.put("/devices/{device_id}", response_model=TuyaDeviceSchema)
async def update_device(device_id: str, req: AddDeviceRequest, request: Request = None):
    """Обновить параметры зарегистрированного устройства."""
    module = _get_tuya_module(request)
    if not module.storage:
        raise HTTPException(status_code=500, detail=make_error_detail(request, "TUYA_STORAGE_UNAVAILABLE", "tuya_storage_unavailable"))

    existing = module.storage.get(device_id)
    if not existing:
        raise HTTPException(status_code=404, detail=make_error_detail(request, "TUYA_DEVICE_NOT_FOUND", "tuya_device_not_found", device_id=device_id))

    existing.name = req.name.strip() if req.name else existing.name
    existing.ip = req.ip.strip() if req.ip else existing.ip
    existing.local_key = req.local_key.strip() if req.local_key else existing.local_key
    existing.protocol_version = req.protocol_version or existing.protocol_version
    existing.category = req.category or existing.category
    existing.mode = req.mode or existing.mode

    return module.storage.upsert(existing)


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, request: Request = None):
    """Удалить устройство из управления."""
    module = _get_tuya_module(request)
    if not module.storage:
        raise HTTPException(status_code=500, detail=make_error_detail(request, "TUYA_STORAGE_UNAVAILABLE", "tuya_storage_unavailable"))

    deleted = module.storage.delete(device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=make_error_detail(request, "TUYA_DEVICE_NOT_FOUND", "tuya_device_not_found", device_id=device_id))
    return {"status": "success", "message": tr(request, "tuya_device_deleted", device_id=device_id)}


@router.post("/devices/{device_id}/command")
async def send_command(device_id: str, req: CommandRequest, request: Request = None):
    """Отправить команду управления на устройство (включение/выключение, DPS)."""
    module = _get_tuya_module(request)
    if not module.storage or not module.controller:
        raise HTTPException(status_code=500, detail=make_error_detail(request, "TUYA_CONTROLLER_UNAVAILABLE", "tuya_controller_unavailable"))

    dev = module.storage.get(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=make_error_detail(request, "TUYA_DEVICE_NOT_FOUND", "tuya_device_not_found", device_id=device_id))

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
        raise HTTPException(status_code=502, detail=make_error_detail(request, "TUYA_COMMAND_FAILED", "tuya_command_failed"))

    return {"status": "success", "device_id": device_id, "mode_used": target_mode}


@router.post("/sync")
async def sync_cloud_devices(request: Request = None):
    """Синхронизировать данные устройств через Tuya Cloud API."""
    module = _get_tuya_module(request)
    if not module.cloud_client:
        raise HTTPException(status_code=400, detail=make_error_detail(request, "TUYA_CLOUD_NOT_CONFIGURED", "tuya_cloud_not_configured"))

    if not module.storage:
        raise HTTPException(status_code=500, detail=make_error_detail(request, "TUYA_STORAGE_UNAVAILABLE", "tuya_storage_unavailable"))

    devices = module.storage.get_all()
    synced_count = 0
    for dev in devices:
        status_list = await module.cloud_client.get_device_status(dev.device_id)
        if status_list is not None:
            dps_map = {item.get("code"): item.get("value") for item in status_list if "code" in item}
            module.storage.update_status(dev.device_id, online=True, dps=dps_map)
            synced_count += 1

    return {"status": "success", "synced_devices": synced_count}
