"""Системные API endpoints для управления модулями."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.plugin.registry import (
    get_loaded_modules,
    get_module_enable_config_schema,
    get_module_settings,
    get_module_settings_definition,
    get_module_views,
    get_modules,
    save_module_settings,
    set_module_enabled,
)

router = APIRouter(prefix="/api/modules", tags=["modules"])


class EnableBody(BaseModel):
    enabled: bool


@router.get("")
async def list_modules(
    with_settings: bool = False,
    only_enabled: bool = False,
) -> dict[str, Any]:
    """Список модулей и их состояние."""
    items = get_modules(with_settings=with_settings, only_enabled=only_enabled)
    return {"items": items}


@router.get("/loaded")
async def loaded_modules() -> dict[str, Any]:
    """Список ID загруженных (включённых) модулей."""
    return {"items": get_loaded_modules()}


@router.get("/config-schema")
async def module_config_schema() -> dict[str, Any]:
    """Схема enable/disable для UI."""
    return get_module_enable_config_schema()


@router.put("/{module_id}/enabled")
async def toggle_module(module_id: str, body: EnableBody) -> dict[str, Any]:
    """Включить/выключить модуль."""
    state = set_module_enabled(module_id, body.enabled)
    return {"module_id": module_id, "enabled": body.enabled, "state": state}


@router.get("/{module_id}/views")
async def module_views(module_id: str) -> dict[str, Any]:
    """UI-маршруты модуля."""
    views = get_module_views(module_id)
    return {"items": views}


@router.get("/{module_id}/settings-definition")
async def module_settings_definition(module_id: str) -> dict[str, Any]:
    """JSON Schema настроек модуля + defaults."""
    definition = get_module_settings_definition(module_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="No settings schema for this module")
    return definition


@router.get("/{module_id}/settings")
async def module_settings_get(module_id: str) -> dict[str, Any]:
    """Текущие настройки модуля."""
    return get_module_settings(module_id)


@router.put("/{module_id}/settings")
async def module_settings_put(module_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Сохранить настройки модуля."""
    save_module_settings(module_id, body)
    return {"ok": True, "module_id": module_id}
