"""Модуль настроек WebUI."""
from fastapi import APIRouter, HTTPException

from backend.core.module_registry import (
    get_loaded_modules,
    get_module_enable_config_schema,
    get_module_settings_definition,
    get_module_state_snapshot,
    get_module_views,
    get_modules,
)
from backend.core.module_state import set_module_enabled
from backend.core.webui_settings import get_webui_settings, save_webui_settings
from pathlib import Path

from backend.modules.stream.core.loader import ModuleLoader


def router_factory() -> APIRouter:
    router = APIRouter()

    def _loader() -> ModuleLoader:
        base = Path(__file__).resolve().parent.parent / "stream"
        ld = ModuleLoader(base_dir=base)
        ld.invalidate_cache()
        return ld

    def _available_backends():
        ld = _loader()
        manifests = ld.manifests()
        names = list(manifests.keys())
        playback_by_output: dict[str, list[str]] = {}
        for name, mf in manifests.items():
            caps = (mf.get("capabilities") or {})
            outputs = caps.get("outputs") or []
            for out in outputs:
                playback_by_output.setdefault(out, []).append(name)
        return names, playback_by_output

    @router.get("/api/settings")
    async def get_settings_api():
        settings = get_webui_settings()
        names, playback_by_output = _available_backends()
        return {
            "modules": settings["modules"],
            "available": {
                "capture": names,
                "playback_udp": names,
            },
            "stream_links": {},
            "playback_backends_by_output": playback_by_output,
            "current_capture_backend": None,
        }

    @router.put("/api/settings")
    async def put_settings_api(body: dict):
        modules = body.get("modules")
        if modules is None:
            raise HTTPException(status_code=400, detail="modules must be provided")
        save_webui_settings({"modules": modules})
        names, playback_by_output = _available_backends()
        return {
            "modules": modules,
            "available": {
                "capture": names,
                "playback_udp": names,
            },
            "stream_links": {},
            "playback_backends_by_output": playback_by_output,
            "current_capture_backend": None,
        }

    @router.get("/api/modules")
    async def list_modules_api(with_settings: bool = False, only_enabled: bool = False):
        """Реестр модулей WebUI (опционально с текущими настройками)."""
        return {
            "items": get_modules(with_settings=with_settings, only_enabled=only_enabled),
            "state": get_module_state_snapshot(),
        }

    @router.put("/api/modules/{module_id}/enabled")
    async def set_module_enabled_api(module_id: str, body: dict):
        """Включить/выключить модуль WebUI. body: { enabled: bool }."""
        enabled = bool(body.get("enabled"))
        state = set_module_enabled(module_id, enabled)
        return {"state": state}

    @router.get("/api/modules/config-schema")
    async def get_modules_config_schema_api():
        """Схема управления включением/выключением модулей и подмодулей."""
        return get_module_enable_config_schema()

    @router.get("/api/modules/loaded")
    async def get_loaded_modules_api():
        """Список реально включенных модулей (manifest-driven)."""
        return {"items": get_loaded_modules()}

    @router.get("/api/modules/{module_id}/views")
    async def get_module_views_api(module_id: str):
        """Список представлений загруженного модуля."""
        views = get_module_views(module_id)
        if not views:
            raise HTTPException(status_code=404, detail="Module not loaded or has no views")
        return {"items": views}

    @router.get("/api/modules/{module_id}/settings-definition")
    async def get_module_settings_definition_api(module_id: str):
        """Схема и default-настройки модуля из manifest.yaml."""
        definition = get_module_settings_definition(module_id)
        if not definition:
            raise HTTPException(status_code=404, detail="Module has no settings schema")
        current = get_webui_settings().get("modules", {}).get(module_id, {})
        return {**definition, "current": current if isinstance(current, dict) else {}}

    @router.get("/api/modules/{module_id}/settings")
    async def get_module_settings_api(module_id: str):
        """Текущие настройки модуля."""
        definition = get_module_settings_definition(module_id)
        if not definition:
            raise HTTPException(status_code=404, detail="Module has no settings schema")
        current = get_webui_settings().get("modules", {}).get(module_id, {})
        return {"module_id": module_id, "settings": current if isinstance(current, dict) else {}}

    @router.put("/api/modules/{module_id}/settings")
    async def put_module_settings_api(module_id: str, body: dict):
        """Сохранить настройки модуля (manifest-driven)."""
        definition = get_module_settings_definition(module_id)
        if not definition:
            raise HTTPException(status_code=404, detail="Module has no settings schema")
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="settings body must be object")
        save_webui_settings({"modules": {module_id: body}})
        current = get_webui_settings().get("modules", {}).get(module_id, {})
        return {"module_id": module_id, "settings": current if isinstance(current, dict) else {}}

    return router
