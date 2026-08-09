"""Реестр загруженных модулей, enable/disable, настройки."""
from __future__ import annotations

import json
import logging
import os
import sys
import asyncio
from copy import deepcopy
from pathlib import Path
from typing import Any

from backend.core.database import get_system_setting, set_system_setting
from backend.core.plugin.manifest import ModuleManifest
from backend.core.events import notify_settings_changed

_log = logging.getLogger("nms.plugin.registry")

# ── In-memory registry ──────────────────────────────────────────────
_manifests: dict[str, ModuleManifest] = {}
_enabled: dict[str, bool] = {}
_instances: dict[str, Any] = {}  # Активные экземпляры модулей (BaseModule)
_errors: dict[str, str] = {}  # Ошибки загрузки модулей


def register_module_error(module_id: str, error: str) -> None:
    """Зарегистрировать ошибку загрузки модуля."""
    _errors[module_id] = error


def clear_module_error(module_id: str) -> None:
    """Очистить ошибку загрузки модуля."""
    _errors.pop(module_id, None)


def get_module_errors() -> dict[str, str]:
    """Получить словарь ошибок всех модулей."""
    return dict(_errors)


def get_module_error(module_id: str) -> str | None:
    """Получить ошибку конкретного модуля."""
    return _errors.get(module_id)


def sync_module_permissions(manifest: ModuleManifest) -> None:
    """Автоматическая синхронизация объявленных разрешений модуля с БД."""
    from backend.core.database import get_db_connection
    perms = []
    if manifest.permissions:
        for p in manifest.permissions:
            cat = p.category or f"Модуль {manifest.name or manifest.id}"
            perms.append((p.id, cat, p.name, p.description or "", manifest.id))
    else:
        # Автодефолтные пермишены для модуля, если они явно не перечислялись
        perms = [
            (f"module.{manifest.id}.view", f"Модуль {manifest.name or manifest.id}", f"Просмотр {manifest.name or manifest.id}", f"Доступ к просмотру интерфейса модуля {manifest.id}", manifest.id),
            (f"module.{manifest.id}.edit", f"Модуль {manifest.name or manifest.id}", f"Настройка {manifest.name or manifest.id}", f"Редактирование параметров модуля {manifest.id}", manifest.id),
            (f"module.{manifest.id}.control", f"Модуль {manifest.name or manifest.id}", f"Управление {manifest.name or manifest.id}", f"Выполнение команд модуля {manifest.id}", manifest.id),
        ]

    try:
        conn = get_db_connection()
        try:
            with conn:
                for p_id, p_cat, p_name, p_desc, p_mod in perms:
                    conn.execute(
                        """
                        INSERT INTO permissions (id, category, name, description, module_id)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            category = excluded.category,
                            name = excluded.name,
                            description = excluded.description,
                            module_id = excluded.module_id
                        """,
                        (p_id, p_cat, p_name, p_desc, p_mod),
                    )
                    # Привязка к Суперпользователю и Админу по умолчанию
                    conn.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('1', ?)", (p_id,))
                    conn.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('2', ?)", (p_id,))
        finally:
            conn.close()
    except Exception as exc:
        _log.warning("Failed to sync permissions for module %s: %s", manifest.id, exc)


def register_manifest(manifest: ModuleManifest, *, enabled: bool = True) -> None:
    """Зарегистрировать манифест модуля в реестре."""
    _manifests[manifest.id] = manifest
    _enabled[manifest.id] = enabled
    sync_module_permissions(manifest)


def get_all_manifests() -> list[ModuleManifest]:
    """Все зарегистрированные манифесты."""
    return list(_manifests.values())


def get_manifest(module_id: str) -> ModuleManifest | None:
    """Получить манифест зарегистрированного модуля по ID."""
    return _manifests.get(module_id)


def unregister_manifest(module_id: str) -> None:
    """Удалить манифест и инстанс модуля из реестра."""
    _manifests.pop(module_id, None)
    _enabled.pop(module_id, None)
    _instances.pop(module_id, None)
    _errors.pop(module_id, None)


def get_all_widgets() -> list[dict[str, Any]]:
    """Получить список виджетов для всех включенных модулей + системные виджеты."""
    widgets: list[dict[str, Any]] = [
        {
            "id": "system-modules",
            "module_id": "system",
            "title": "modulesCount",
            "description": "Обзор и статус установленных модулей системы",
            "component": "ModulesWidget",
            "endpoint": "/api/modules/summary_widget",
            "size": "large",
            "type": "list",
            "default_active": True,
        }
    ]
    for manifest in _manifests.values():
        if _enabled.get(manifest.id, manifest.enabled_by_default):
            for w in manifest.widgets:
                w_dict = w.model_dump()
                w_dict["module_id"] = manifest.id
                widgets.append(w_dict)
    return widgets



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


async def shutdown_all() -> None:
    """Корректная остановка всех модулей с методом stop()."""
    for mid, inst in reversed(list(_instances.items())):
        try:
            if hasattr(inst, "stop"):
                if asyncio.iscoroutinefunction(inst.stop):
                    await inst.stop()
                else:
                    inst.stop()
                _log.info("Module %s stopped", mid)
        except Exception as exc:
            _log.warning("Module %s stop failed: %s", mid, exc)
    _instances.clear()


# ── Persistent Storage (SQLite system_settings table) ────────────────

def _load_raw_settings() -> dict[str, Any]:
    """Загрузка настроек всех модулей из БД system_settings."""
    db_data = get_system_setting("modules_settings", None)
    if db_data is not None and isinstance(db_data, dict):
        if "modules" in db_data:
            return db_data
        return {"modules": db_data}
    return {"modules": {}}


def _save_raw_settings(data: dict[str, Any]) -> None:
    """Сохранить настройки всех модулей в базу данных."""
    set_system_setting("modules_settings", data)


def _deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def is_module_enabled(module_id: str, default: bool = True) -> bool:
    data = _load_raw_settings()
    mod_data = data.get("modules", {}).get(module_id)
    if isinstance(mod_data, dict) and "enabled" in mod_data:
        return bool(mod_data["enabled"])
    return default


def is_module_active(module_id: str) -> bool:
    """Проверить, зарегистрирован ли и включен ли модуль в реестре."""
    manifest = _manifests.get(module_id)
    if not manifest:
        return False
    return _enabled.get(module_id, manifest.enabled_by_default)


def set_module_enabled(module_id: str, enabled: bool) -> dict[str, bool]:
    data = _load_raw_settings()
    modules = data.get("modules") or {}
    if module_id not in modules:
        modules[module_id] = {"enabled": enabled, "settings": {}}
    else:
        modules[module_id]["enabled"] = bool(enabled)
    data["modules"] = modules
    _save_raw_settings(data)
    _enabled[module_id] = enabled
    notify_settings_changed(module_id)

    from backend.core.bus import event_bus
    if enabled:
        event_bus.publish("core.modules.enabled", {"module_id": module_id}, is_core=True)
    else:
        event_bus.publish("core.modules.disabled", {"module_id": module_id}, is_core=True)
        from backend.core.plugin.context import cleanup_module_events, cleanup_module_scheduler
        cleanup_module_events(module_id)
        cleanup_module_scheduler(module_id)

    # Возвращаем плоский словарь для совместимости с текущим API, если нужно
    return {mid: bool(m.get("enabled", True)) for mid, m in modules.items() if isinstance(m, dict)}


def get_webui_settings() -> dict[str, Any]:
    """Возвращает настройки в формате для фронтенда (совместимость)."""
    data = _load_raw_settings()
    modules = data.get("modules") or {}
    # Фронт ожидает {"modules": {"astra": {...}}}
    return {"modules": {mid: m.get("settings", {}) for mid, m in modules.items() if isinstance(m, dict)}}


def save_webui_settings(update: dict[str, Any]) -> None:
    """Сохранить настройки."""
    data = _load_raw_settings()
    modules = data.get("modules") or {}

    update_mods = update.get("modules") or {}
    for mid, settings in update_mods.items():
        if mid not in modules:
            modules[mid] = {"enabled": True, "settings": {}}
        modules[mid]["settings"] = _deep_merge(modules[mid].get("settings") or {}, settings)

    data["modules"] = modules
    _save_raw_settings(data)

    for mid in update_mods:
        notify_settings_changed(mid)


def get_module_settings(module_id: str) -> dict[str, Any]:
    data = _load_raw_settings()
    mod_data = data.get("modules", {}).get(module_id)
    if isinstance(mod_data, dict):
        return mod_data.get("settings") or {}
    return {}


def save_module_settings(module_id: str, values: dict[str, Any]) -> None:
    save_webui_settings({"modules": {module_id: values}})


def get_security_settings() -> dict[str, Any]:
    env_disable = os.getenv("NMS_DISABLE_AUTH", "").lower() in ("1", "true", "yes")
    env_enable = os.getenv("NMS_AUTH_ENABLED", "").lower() in ("0", "false", "no")
    cmd_disable = any(arg in sys.argv for arg in ("--no-auth", "--disable-auth", "--auth-disabled"))

    if env_disable or env_enable or cmd_disable:
        auth_enabled = False
    else:
        auth_enabled = bool(get_system_setting("sec_auth_enabled", True))

    return {
        "auth_enabled": auth_enabled,
        "mandatory_password_change": bool(get_system_setting("sec_mandatory_password_change", True)),
        "max_login_attempts": int(get_system_setting("sec_max_login_attempts", 5)),
        "lockout_duration": int(get_system_setting("sec_lockout_duration", 30)),
        "session_ttl_hours": int(get_system_setting("sec_session_ttl_hours", 12)),
        "inactivity_timeout_mins": int(get_system_setting("sec_inactivity_timeout_mins", 30)),
        "force_mfa": bool(get_system_setting("sec_force_mfa", False)),
        "min_password_length": int(get_system_setting("sec_min_password_length", 8)),
        "require_uppercase": bool(get_system_setting("sec_require_uppercase", False)),
        "require_digits": bool(get_system_setting("sec_require_digits", False)),
        "require_special_chars": bool(get_system_setting("sec_require_special_chars", False)),
        "ip_whitelist": str(get_system_setting("sec_ip_whitelist", "")),
    }


def save_security_settings(update: dict[str, Any]) -> None:
    if "auth_enabled" in update:
        set_system_setting("sec_auth_enabled", bool(update["auth_enabled"]))
    if "mandatory_password_change" in update:
        set_system_setting("sec_mandatory_password_change", bool(update["mandatory_password_change"]))
    if "max_login_attempts" in update:
        set_system_setting("sec_max_login_attempts", int(update["max_login_attempts"]))
    if "lockout_duration" in update:
        set_system_setting("sec_lockout_duration", int(update["lockout_duration"]))
    if "session_ttl_hours" in update:
        set_system_setting("sec_session_ttl_hours", int(update["session_ttl_hours"]))
    if "inactivity_timeout_mins" in update:
        set_system_setting("sec_inactivity_timeout_mins", int(update["inactivity_timeout_mins"]))
    if "force_mfa" in update:
        set_system_setting("sec_force_mfa", bool(update["force_mfa"]))
    if "min_password_length" in update:
        set_system_setting("sec_min_password_length", int(update["min_password_length"]))
    if "require_uppercase" in update:
        set_system_setting("sec_require_uppercase", bool(update["require_uppercase"]))
    if "require_digits" in update:
        set_system_setting("sec_require_digits", bool(update["require_digits"]))
    if "require_special_chars" in update:
        set_system_setting("sec_require_special_chars", bool(update["require_special_chars"]))
    if "ip_whitelist" in update:
        set_system_setting("sec_ip_whitelist", str(update["ip_whitelist"]))




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
            "optional_deps": manifest.optional_deps,
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
