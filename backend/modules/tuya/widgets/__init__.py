"""Логика и обработчики виджетов модуля Tuya."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException
from backend.core.plugin.registry import get_instance

widget_router = APIRouter(prefix="/widgets", tags=["tuya-widgets"])


@widget_router.get("/summary")
async def get_tuya_summary_widget() -> dict[str, Any]:
    """Данные для виджета сводки устройств Tuya."""
    instance = get_instance("tuya")
    if not instance or not instance.storage:
        return {"total": 0, "online": 0, "offline": 0}
    devices = instance.storage.get_all()
    online_count = sum(1 for d in devices if d.online)
    return {
        "total": len(devices),
        "online": online_count,
        "offline": len(devices) - online_count,
        "devices": [d.model_dump() for d in devices],
    }
