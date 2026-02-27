"""Реестр загруженных модулей, enable/disable, настройки."""
from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

from backend.core.config import _instances_path
from backend.core.plugin.manifest import ModuleManifest

_log = logging.getLogger("nms.plugin.registry")

# ── In-memory registry ──────────────────────────────────────────────
_manifests: dict[str, ModuleManifest] = {}
_enabled: dict[str, bool] = {}
_instances: dict[str, Any] = {}  # Активные экземпляры модулей (BaseModule)


def register_manifest(manifest: ModuleManifest, *, enabled: bool = True) -> None:
    """Зарегистрировать манифест модуля в реестре."""
    _manifests[manifest.id] = manifest
    _enabled[manifest.id] = enabled


def get_all_manifests() -> list[ModuleManifest]:
    """Все зарегистрированные манифесты."""
    return list(_manifests.values())


# ── Module instance management ─────────────────────────────────────────────────
def register_instance(module_id: str, instance: Any) -> None:
    """Зарегистрировать активный экземпляр модуля."""
    _instances[module_id] = instance
    _log.debug("Instance registered: %s", module_id)


def get_instance(module_id: str) -> Any | None:
    """Получить экземпляр модуля по ID."""
    return _instances.get(module_id)


def get_all_instances() -> dict[str, Any]:
    """Все активные экземпляры."""
    return dict(_instances)


def shutdown_all() -> None:
    """Корректная остановка всех модулей с методом stop()."""
    for mid, inst in reversed(list(_instances.items())):
        try:
            if hasattr(inst, "stop"):
                inst.stop()
                _log.info("Module %s stopped", mid)
        except Exception as exc:
            _log.warning("Module %s stop failed: %s", mid, exc)
    _instances.clear()


# ── Enable / Disable (persistent state) ─────────────────────────────
def _state_path() -> Path:
    return _instances_path().parent / "modules_state.json"


def _load_state() -> dict[str, bool]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): bool(v) for k, v in data.items()}


def _save_state(state: dict[str, bool]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def is_module_enabled(module_id: str, default: bool = True) -> bool:
    state = _load_state()
    return state.get(module_id, default)


def set_module_enabled(module_id: str, enabled: bool) -> dict[str, bool]:
    state = _load_state()
    state[module_id] = bool(enabled)
    _save_state(state)
    _enabled[module_id] = enabled
    return state


# ── Settings (webui_settings.json) ──────────────────────────────────
def _settings_path() -> Path:
    return _instances_path().parent / "webui_settings.json"


def _deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def get_webui_settings() -> dict[str, Any]:
    """Загрузить настройки WebUI из webui_settings.json."""
    path = _settings_path()
    if not path.exists():
        return {"modules": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    return {"modules": data.get("modules") or {}}


def save_webui_settings(update: dict[str, Any]) -> None:
    """Сохранить настройки."""
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = get_webui_settings()
    if "modules" in update and isinstance(update["modules"], dict):
        current["modules"] = _deep_merge(current["modules"], update["modules"])
    path.write_text(
        json.dumps({"modules": current["modules"]}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_module_settings(module_id: str) -> dict[str, Any]:
    """Текущие настройки конкретного модуля."""
    return get_webui_settings().get("modules", {}).get(module_id, {})


def save_module_settings(module_id: str, values: dict[str, Any]) -> None:
    """Сохранить настройки конкретного модуля."""
    save_webui_settings({"modules": {module_id: values}})


# ── Query helpers ───────────────────────────────────────────────────
def get_modules(
    *, with_settings: bool = False, only_enabled: bool = False
) -> list[dict[str, Any]]:
    """Список модулей для API."""
    modules = []
    for manifest in _manifests.values():
        mod = manifest.to_api_dict()
        mod["enabled"] = _enabled.get(manifest.id, manifest.enabled_by_default)
        modules.append(mod)

    if only_enabled:
        modules = [m for m in modules if m.get("enabled")]

    if with_settings:
        settings = get_webui_settings().get("modules", {})
        for mod in modules:
            mod["settings_current"] = settings.get(mod["id"])

    return modules


def get_loaded_modules() -> list[str]:
    """ID включённых модулей."""
    return [mid for mid, en in _enabled.items() if en]


def get_module_views(module_id: str) -> list[dict[str, Any]]:
    """UI-маршруты конкретного модуля (включая субмодули)."""
    routes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for manifest in _manifests.values():
        if manifest.id == module_id or manifest.parent == module_id:
            for route in manifest.routes:
                if route.path not in seen:
                    seen.add(route.path)
                    routes.append({
                        "path": route.path,
                        "name": route.name,
                        "meta": route.meta.model_dump(exclude_none=True),
                    })
    return routes


def _defaults_from_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Извлечь значения по умолчанию из JSON Schema."""
    defaults: dict[str, Any] = {}
    properties = schema.get("properties") or {}
    for key, prop in properties.items():
        if not isinstance(prop, dict):
            continue
        if "default" in prop:
            defaults[str(key)] = prop["default"]
        elif prop.get("type") == "object":
            nested = _defaults_from_schema(prop)
            if nested:
                defaults[str(key)] = nested
    return defaults


def get_module_settings_schema(module_id: str) -> dict[str, Any] | None:
    manifest = _manifests.get(module_id)
    if not manifest or not manifest.config_schema:
        return None
    return manifest.config_schema


def get_module_settings_definition(module_id: str) -> dict[str, Any] | None:
    schema = get_module_settings_schema(module_id)
    if not schema:
        return None
    return {
        "module_id": module_id,
        "schema": schema,
        "defaults": _defaults_from_schema(schema),
        "current": get_module_settings(module_id),
    }


def get_module_enable_config_schema() -> dict[str, Any]:
    """Схема enable/disable для модулей (для UI)."""
    grouped: dict[str, dict[str, Any]] = {}
    for manifest in _manifests.values():
        node = {
            "id": manifest.id,
            "title": manifest.name or manifest.id,
            "enabled": _enabled.get(manifest.id, manifest.enabled_by_default),
            "type": manifest.type,
            "is_submodule": manifest.parent is not None,
            "deps": manifest.deps,
            "children": [],
        }
        if manifest.parent:
            grouped.setdefault(manifest.parent, {"children": []})["children"].append(node)
        else:
            grouped.setdefault(manifest.id, {"node": node, "children": []})
            grouped[manifest.id]["node"] = node

    items: list[dict[str, Any]] = []
    for bucket in grouped.values():
        node = bucket.get("node")
        if not node:
            continue
        node["children"] = sorted(bucket.get("children", []), key=lambda x: x["id"])
        items.append(node)
    items.sort(key=lambda x: x["id"])

    return {"version": "1.0.0", "type": "module_enable_schema", "items": items}
