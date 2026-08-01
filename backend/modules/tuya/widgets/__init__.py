"""Логика и обработчики виджетов модуля Tuya."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from backend.core.plugin.registry import get_instance
from backend.core.plugin.widgets import (
    WidgetAction,
    WidgetDataResponse,
    WidgetMetric,
    WidgetStatus,
    WidgetType,
)

widget_router = APIRouter(prefix="/widgets", tags=["tuya-widgets"])


@widget_router.get("/summary")
async def get_tuya_summary_widget() -> dict[str, Any]:
    """Данные для виджета сводки устройств Tuya в едином формате WidgetDataResponse."""
    instance = get_instance("tuya")
    devices = instance.storage.get_all() if (instance and instance.storage) else []
    total = len(devices)
    online_count = sum(1 for d in devices if d.online)
    offline_count = total - online_count

    widget_data = WidgetDataResponse(
        status=WidgetStatus.OK if total > 0 else WidgetStatus.INFO,
        type=WidgetType.SUMMARY,
        title="tuyaWidgetTitle",
        metrics=[
            WidgetMetric(
                id="total",
                label="tuyaTotalDevices",
                value=total,
                status=WidgetStatus.INFO,
                icon="devices",
            ),
            WidgetMetric(
                id="online",
                label="tuyaOnlineDevices",
                value=online_count,
                status=WidgetStatus.OK,
                icon="check_circle",
            ),
            WidgetMetric(
                id="offline",
                label="tuyaOfflineDevices",
                value=offline_count,
                status=WidgetStatus.WARNING if offline_count > 0 else WidgetStatus.INFO,
                icon="error",
            ),
        ],
        actions=[
            WidgetAction(
                label="tuyaManageDevices",
                path="/tuya",
                icon="arrow_forward",
            )
        ],
        extra={
            "total": total,
            "online": online_count,
            "offline": offline_count,
            "devices": [d.model_dump() for d in devices],
        },
    )

    return widget_data.model_dump()

