"""Реестр модулей WebUI для nms-webui."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from backend.core.module_state import is_module_enabled, get_module_state
from backend.core.ui_manifest import parse_views_from_manifest
from backend.core.webui_settings import get_webui_settings

_LEGACY_MODULES: list[dict[str, Any]] = [
    {
        "id": "cesbo-astra",
        "name": "Cesbo Astra",
        "version": "1.0.0",
        "deps": [],
        "permissions": [],
        "settings": [],
        "menu": {
            "location": "sidebar",
            "group": "Cesbo Astra",
            "items": [
                {"path": "/", "label": "Общая информация"},
                {"path": "/instances", "label": "Управление экземплярами"},
                {"path": "/channels", "label": "Каналы"},
                {"path": "/monitors", "label": "Мониторы"},
                {"path": "/subscribers", "label": "Подписка"},
                {"path": "/dvb", "label": "DVB-адаптеры"},
                {"path": "/system", "label": "Система"},
            ],
        },
        "routes": [
            {"path": "/", "name": "Overview", "meta": {"title": "Общая информация"}},
            {"path": "/instances", "name": "Instances", "meta": {"title": "Управление экземплярами"}},
            {"path": "/channels", "name": "Channels", "meta": {"title": "Каналы"}},
            {"path": "/monitors", "name": "Monitors", "meta": {"title": "Мониторы"}},
            {"path": "/subscribers", "name": "Subscribers", "meta": {"title": "Подписка"}},
            {"path": "/dvb", "name": "Dvb", "meta": {"title": "DVB-адаптеры"}},
            {"path": "/system", "name": "System", "meta": {"title": "Система"}},
        ],
    },
    {
        "id": "settings",
        "name": "Настройки",
        "version": "1.0.0",
        "deps": [],
        "permissions": [],
        "settings": [],
        "menu": {
            "location": "footer",
            "items": [{"path": "/settings", "label": "Настройки", "icon": "settings"}],
        },
        "routes": [{"path": "/settings", "name": "Settings", "meta": {"title": "Настройки"}}],
    },
    {
        "id": "system-api",
        "name": "System API",
        "version": "1.0.0",
        "deps": [],
        "permissions": [],
        "settings": [],
        "menu": None,
        "routes": [],
    },
    {
        "id": "system",
        "name": "Система",
        "version": "1.0.0",
        "deps": ["system-api"],
        "permissions": [],
        "settings": [],
        "menu": {
            "location": "sidebar",
            "group": "Cesbo Astra",
            "items": [
                {"path": "/system", "label": "Система"},
            ],
        },
        "routes": [{"path": "/system", "name": "System", "meta": {"title": "Система"}}],
    },
]

_LEGACY_BY_ID: dict[str, dict[str, Any]] = {m["id"]: deepcopy(m) for m in _LEGACY_MODULES}


def _safe_load_yaml(path: Path) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _discover_manifest_rows(modules_dir: Path) -> list[dict[str, Any]]:
    if not modules_dir.exists():
        return []
    rows: list[dict[str, Any]] = []

    def _walk_submodules(parent_dir: Path, parent_id: str, root_id: str) -> None:
        submodules_dir = parent_dir / "submodules"
        if not submodules_dir.exists():
            return
        for submodule_dir in sorted([p for p in submodules_dir.iterdir() if p.is_dir()]):
            sub_manifest_path = next(iter(sorted(submodule_dir.glob("manifest.y*ml"))), None)
            if sub_manifest_path is None:
                continue
            data = _safe_load_yaml(sub_manifest_path)
            if data is None:
                continue
            raw_sub_id = str(data.get("id") or submodule_dir.name)
            sub_id = raw_sub_id if "." in raw_sub_id else f"{parent_id}.{raw_sub_id}"
            deps = data.get("deps") if isinstance(data.get("deps"), list) else []
            if parent_id not in deps:
                deps = [*deps, parent_id]
            rows.append({
                "id": sub_id,
                "name": data.get("name") or raw_sub_id,
                "version": str(data.get("version") or "1.0.0"),
                "deps": deps,
                "enabled_by_default": bool(data.get("enabled_by_default", True)),
                "type": str(data.get("type") or "optional"),
                "config_schema": data.get("config_schema") if isinstance(data.get("config_schema"), dict) else None,
                "menu": data.get("menu") if isinstance(data.get("menu"), dict) else None,
                "routes": [v.to_route_dict() for v in parse_views_from_manifest(data)],
                "parent_id": parent_id,
                "is_submodule": True,
                "root": str(submodule_dir),
                "root_module_id": root_id,
            })
            _walk_submodules(submodule_dir, sub_id, root_id)

    for module_dir in sorted([p for p in modules_dir.iterdir() if p.is_dir()]):
        root_manifest = next(iter(sorted(module_dir.glob("manifest.y*ml"))), None)
        if root_manifest is None:
            continue
        root_data = _safe_load_yaml(root_manifest)
        if root_data is None:
            continue
        root_id = str(root_data.get("id") or module_dir.name)
        rows.append({
            "id": root_id,
            "name": root_data.get("name") or root_id,
            "version": str(root_data.get("version") or "1.0.0"),
            "deps": root_data.get("deps") if isinstance(root_data.get("deps"), list) else [],
            "enabled_by_default": bool(root_data.get("enabled_by_default", True)),
            "type": str(root_data.get("type") or "optional"),
            "config_schema": root_data.get("config_schema") if isinstance(root_data.get("config_schema"), dict) else None,
            "menu": root_data.get("menu") if isinstance(root_data.get("menu"), dict) else None,
            "routes": [v.to_route_dict() for v in parse_views_from_manifest(root_data)],
            "parent_id": None,
            "is_submodule": False,
            "root": str(module_dir),
            "root_module_id": root_id,
        })
        _walk_submodules(module_dir, root_id, root_id)
    return rows


def _row_to_module(row: dict[str, Any]) -> dict[str, Any]:
    module_id = str(row.get("id") or "")
    legacy = deepcopy(_LEGACY_BY_ID.get(module_id, {}))
    module = {
        "id": module_id,
        "name": row.get("name") or module_id,
        "version": row.get("version") or "1.0.0",
        "deps": row.get("deps") or [],
        "enabled_by_default": bool(row.get("enabled_by_default", True)),
        "type": row.get("type") or "optional",
        "config_schema": row.get("config_schema") if isinstance(row.get("config_schema"), dict) else None,
        "permissions": legacy.get("permissions", []),
        "settings": legacy.get("settings", []),
        "menu": row.get("menu") if isinstance(row.get("menu"), dict) else legacy.get("menu"),
        "routes": row.get("routes") if isinstance(row.get("routes"), list) and row.get("routes") else legacy.get("routes", []),
        "parent_id": row.get("parent_id"),
        "is_submodule": bool(row.get("is_submodule", False)),
        "root": row.get("root"),
        "root_module_id": row.get("root_module_id"),
    }
    if module["config_schema"] and not any(r.get("path") == f"/modules/{module_id}/settings" for r in module["routes"]):
        module["routes"].append(
            {
                "path": f"/modules/{module_id}/settings",
                "name": f"{module_id.replace('.', '_')}_settings",
                "meta": {"title": f"{module['name']} — Настройки", "settings_view": True},
            }
        )
    return module


def _load_modules() -> list[dict[str, Any]]:
    modules_dir = Path(__file__).resolve().parent.parent / "modules"
    discovered = [_row_to_module(row) for row in _discover_manifest_rows(modules_dir)]
    if discovered:
        return discovered
    # Фоллбек для legacy-конфигурации, если манифесты временно отсутствуют.
    return deepcopy(_LEGACY_MODULES)


def get_modules(with_settings: bool = False, only_enabled: bool = False) -> list[dict[str, Any]]:
    modules = _load_modules()
    enabled_by_id: dict[str, bool] = {}
    for mod in modules:
        mod_id = mod.get("id", "")
        parent_id = mod.get("parent_id")
        parent_enabled = enabled_by_id.get(parent_id, True) if parent_id else True
        mod_default = bool(mod.get("enabled_by_default", True))
        mod_enabled = is_module_enabled(mod_id, default=mod_default) if parent_enabled else False
        mod["enabled"] = mod_enabled
        enabled_by_id[mod_id] = mod_enabled
    if only_enabled:
        modules = [mod for mod in modules if mod.get("enabled")]
    if not with_settings:
        return modules
    settings = get_webui_settings().get("modules", {})
    for mod in modules:
        mod_id = mod.get("id")
        mod["settings_current"] = settings.get(mod_id)
    return modules


def get_module_state_snapshot() -> dict[str, bool]:
    return get_module_state()


def get_module_enable_config_schema() -> dict[str, Any]:
    """Схема конфигурации enable/disable для модулей и подмодулей."""
    modules = get_modules(with_settings=False, only_enabled=False)
    grouped: dict[str, dict[str, Any]] = {}
    for mod in modules:
        parent_id = mod.get("parent_id")
        mod_id = str(mod.get("id") or "")
        mod_node = {
            "id": mod_id,
            "title": mod.get("name") or mod_id,
            "enabled": bool(mod.get("enabled", True)),
            "type": mod.get("type") or "optional",
            "is_submodule": bool(mod.get("is_submodule", False)),
            "deps": mod.get("deps") or [],
            "children": [],
        }
        if parent_id:
            grouped.setdefault(str(parent_id), {"children": []})["children"].append(mod_node)
            continue
        grouped.setdefault(mod_id, {"node": mod_node, "children": []})
        grouped[mod_id]["node"] = mod_node

    items: list[dict[str, Any]] = []
    for module_id, bucket in grouped.items():
        node = bucket.get("node")
        if not node:
            continue
        node["children"] = sorted(bucket.get("children", []), key=lambda x: x["id"])
        items.append(node)
    items.sort(key=lambda x: x["id"])
    return {
        "version": "1.0.0",
        "type": "module_enable_schema",
        "items": items,
    }


def get_loaded_modules() -> list[str]:
    return [str(mod.get("id")) for mod in get_modules(with_settings=False, only_enabled=True)]


def get_module_views(module_id: str) -> list[dict[str, Any]]:
    for mod in get_modules(with_settings=False, only_enabled=True):
        if str(mod.get("id")) == module_id:
            routes = mod.get("routes")
            return routes if isinstance(routes, list) else []
    return []


def _defaults_from_schema(schema: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    for key, prop in properties.items():
        if not isinstance(prop, dict):
            continue
        if "default" in prop:
            defaults[str(key)] = prop.get("default")
            continue
        if prop.get("type") == "object":
            nested = _defaults_from_schema(prop)
            if nested:
                defaults[str(key)] = nested
    return defaults


def get_module_settings_schema(module_id: str) -> dict[str, Any] | None:
    for mod in get_modules(with_settings=False, only_enabled=False):
        if str(mod.get("id")) != module_id:
            continue
        schema = mod.get("config_schema")
        if isinstance(schema, dict):
            return schema
        return None
    return None


def get_module_settings_definition(module_id: str) -> dict[str, Any] | None:
    schema = get_module_settings_schema(module_id)
    if not schema:
        return None
    return {
        "module_id": module_id,
        "schema": schema,
        "defaults": _defaults_from_schema(schema),
    }
