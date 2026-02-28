"""Сканер и загрузчик модулей по manifest.yaml."""
from __future__ import annotations

import importlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, FastAPI

from backend.core.plugin.context import ModuleContext
from backend.core.plugin.manifest import ModuleManifest
from backend.core.plugin.registry import is_module_enabled
from backend.core.plugin.resolver import toposort_modules

_log = logging.getLogger("nms.plugin.loader")


def _safe_load_yaml(path: Path) -> dict[str, Any] | None:
    """Безопасно загрузить YAML-файл."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        _log.warning("Failed to read manifest %s: %s", path, exc)
        return None
    if not isinstance(data, dict):
        _log.warning("Manifest %s must be a mapping", path)
        return None
    return data


def _parse_manifest(
    path: Path,
    parent_id: str | None = None,
) -> ModuleManifest | None:
    """Парсинг manifest.yaml через Pydantic."""
    data = _safe_load_yaml(path)
    if data is None:
        return None
    try:
        # Нормализация id для субмодулей
        raw_id = str(data.get("id") or path.parent.name)
        if parent_id and "." not in raw_id:
            data["id"] = f"{parent_id}.{raw_id}"
        else:
            data["id"] = raw_id

        if parent_id:
            data["parent"] = parent_id
            # Гарантируем, что родитель в deps
            deps = data.get("deps") or []
            if not isinstance(deps, list):
                deps = [deps]
            if parent_id not in deps:
                deps.append(parent_id)
            data["deps"] = deps

        # Нормализация entrypoints.router в список
        entrypoints = data.get("entrypoints") or {}
        if isinstance(entrypoints, dict):
            router = entrypoints.get("router")
            if isinstance(router, str):
                entrypoints["router"] = [router]
            services = entrypoints.get("services")
            if isinstance(services, str):
                entrypoints["services"] = [services]
        data["entrypoints"] = entrypoints

        return ModuleManifest(**data)
    except Exception as exc:
        _log.warning("Failed to parse manifest %s: %s", path, exc)
        return None


def discover_manifests(modules_dir: Path) -> list[ModuleManifest]:
    """Сканирует modules/ и возвращает все manifest.yaml (включая субмодули)."""
    if not modules_dir.exists():
        _log.info("Modules directory %s does not exist — no modules to load", modules_dir)
        return []

    manifests: list[ModuleManifest] = []

    def _walk_submodules(parent_dir: Path, parent_id: str) -> None:
        submodules_dir = parent_dir / "submodules"
        if not submodules_dir.exists():
            return
        for subdir in sorted(p for p in submodules_dir.iterdir() if p.is_dir()):
            manifest_path = next(iter(sorted(subdir.glob("manifest.y*ml"))), None)
            if manifest_path is None:
                continue
            manifest = _parse_manifest(manifest_path, parent_id=parent_id)
            if manifest is None:
                continue
            manifests.append(manifest)
            _walk_submodules(subdir, manifest.id)

    for module_dir in sorted(p for p in modules_dir.iterdir() if p.is_dir()):
        manifest_path = next(iter(sorted(module_dir.glob("manifest.y*ml"))), None)
        if manifest_path is None:
            continue
        manifest = _parse_manifest(manifest_path)
        if manifest is None:
            continue
        manifests.append(manifest)
        _walk_submodules(module_dir, manifest.id)

    return manifests


def _import_from_path(dotted_path: str) -> Any:
    """Импортировать объект по 'module.path:attribute'."""
    module_path, sep, attr = dotted_path.partition(":")
    if not module_path:
        raise ValueError("entrypoint path is empty")
    mod = importlib.import_module(module_path)
    return getattr(mod, attr) if sep else mod


def _call_with_fallbacks(fn: Callable[..., Any], *args: Any) -> Any:
    """Вызов функции с уменьшением числа аргументов при TypeError."""
    try:
        return fn(*args)
    except TypeError:
        try:
            return fn(*args[:1])
        except TypeError:
            return fn()


def _load_router(entrypoint: str, app: FastAPI, ctx: ModuleContext) -> None:
    """Загрузить и зарегистрировать API-роутер модуля."""
    try:
        factory = _import_from_path(entrypoint)
        router = _call_with_fallbacks(factory, ctx)
        if not isinstance(router, APIRouter):
            raise TypeError("router factory must return APIRouter")
        app.include_router(router)
        _log.info("Module %s: router registered via %s", ctx.module_id, entrypoint)
    except Exception as exc:
        _log.warning("Module %s: router entrypoint failed (%s)", ctx.module_id, exc)


def _load_service(entrypoint: str, app: FastAPI, ctx: ModuleContext) -> None:
    """Зарегистрировать сервис модуля."""
    try:
        registrar = _import_from_path(entrypoint)
        _call_with_fallbacks(registrar, app, ctx)
        _log.info("Module %s: service registered via %s", ctx.module_id, entrypoint)
    except Exception as exc:
        _log.warning("Module %s: service entrypoint failed (%s)", ctx.module_id, exc)


def _call_hook(entrypoint: str, ctx: ModuleContext) -> None:
    """Вызвать lifecycle hook."""
    try:
        hook = _import_from_path(entrypoint)
        _call_with_fallbacks(hook, ctx)
        _log.info("Module %s: hook executed (%s)", ctx.module_id, entrypoint)
    except Exception as exc:
        _log.warning("Module %s: hook failed (%s)", ctx.module_id, exc)


def _load_factory(entrypoint: str, ctx: ModuleContext) -> Any | None:
    """Создать экземпляр модуля через factory entrypoint."""
    try:
        factory_fn = _import_from_path(entrypoint)
        instance = _call_with_fallbacks(factory_fn, ctx)
        _log.info("Module %s: instance created via %s", ctx.module_id, entrypoint)
        return instance
    except Exception as exc:
        _log.warning("Module %s: factory failed (%s)", ctx.module_id, exc)
        return None


def _load_settings_schema(entrypoint: str, ctx: ModuleContext) -> dict | None:
    """Загрузить динамическую схему настроек из settings entrypoint."""
    try:
        settings_fn = _import_from_path(entrypoint)
        schema = _call_with_fallbacks(settings_fn, ctx)
        _log.info("Module %s: settings schema loaded via %s", ctx.module_id, entrypoint)
        return schema
    except Exception as exc:
        _log.warning("Module %s: settings entrypoint failed (%s)", ctx.module_id, exc)
        return None


def load_all_modules(app: FastAPI, modules_dir: Path | None = None) -> None:
    """Обнаружить, отсортировать и загрузить все модули."""
    if modules_dir is None:
        modules_dir = Path(__file__).resolve().parent.parent.parent / "modules"

    raw = discover_manifests(modules_dir)
    if not raw:
        _log.info("No modules found in %s", modules_dir)
        return

    sorted_manifests = toposort_modules(raw)

    # Импортируем registry здесь, чтобы избежать циклических импортов
    from backend.core.plugin.registry import register_manifest, register_instance

    enabled_by_id: dict[str, bool] = {}

    for manifest in sorted_manifests:
        # Проверяем, удовлетворяются ли все зависимости
        deps_satisfied = True
        missing_dep = None
        for dep in manifest.deps:
            # Зависимость считается выполненной только если она успешно загружена и включена
            if not enabled_by_id.get(dep, False):
                deps_satisfied = False
                missing_dep = dep
                break

        # Читаем конфигурацию
        enabled = is_module_enabled(manifest.id, default=manifest.enabled_by_default)

        # Fail-fast: отключаем модуль принудительно, если зависимости не соблюдены
        if not deps_satisfied:
            enabled = False
            enabled_by_id[manifest.id] = False
            
            # Разделяем логирование: для отсутствующего родителя — info (ожидаемо), для прочих deps — warning
            if manifest.parent == missing_dep:
                _log.info("Module %s skipped (parent %s disabled or missing)", manifest.id, missing_dep)
            else:
                _log.warning(
                    "Module %s cannot be enabled: dependency '%s' is missing or disabled",
                    manifest.id, missing_dep
                )
        else:
            enabled_by_id[manifest.id] = enabled

        # Регистрируем манифест в реестре (даже если отключён — для UI)
        register_manifest(manifest, enabled=enabled)

        if not enabled:
            if deps_satisfied:
                _log.info("Module %s disabled; skipping entrypoints", manifest.id)
            continue

        # Создаём контекст
        ctx = ModuleContext(
            module_id=manifest.id,
            root=modules_dir / manifest.id.split(".")[0],
            manifest=manifest.to_api_dict(),
            parent_module_id=manifest.parent,
            is_submodule=manifest.parent is not None,
        )

        # ── Factory: создание экземпляра модуля ──────────────────────
        ep = manifest.entrypoints
        instance = None
        if ep.factory:
            instance = _load_factory(str(ep.factory), ctx)
            if instance is not None:
                register_instance(manifest.id, instance)
                # Вызов lifecycle: init()
                if hasattr(instance, "init"):
                    try:
                        instance.init()
                        _log.info("Module %s: init() completed", manifest.id)
                    except Exception as exc:
                        _log.warning("Module %s: init() failed (%s)", manifest.id, exc)
                # Вызов lifecycle: start()
                if hasattr(instance, "start"):
                    try:
                        instance.start()
                        _log.info("Module %s: start() completed", manifest.id)
                    except Exception as exc:
                        _log.warning("Module %s: start() failed (%s)", manifest.id, exc)

        # ── Router: регистрация API ──────────────────────────────────
        routers = ep.router if isinstance(ep.router, list) else ([ep.router] if ep.router else [])
        for r in routers:
            if r:
                _load_router(str(r), app, ctx)

        # ── Services: регистрация сервисов ───────────────────────────
        services = ep.services if isinstance(ep.services, list) else ([ep.services] if ep.services else [])
        for s in services:
            if s:
                _load_service(str(s), app, ctx)

        # ── Settings: динамическая схема настроек ────────────────────
        if ep.settings:
            dynamic_schema = _load_settings_schema(str(ep.settings), ctx)
            if dynamic_schema:
                # Объединяем (merge) динамическую схему с существующей в манифесте
                if not manifest.config_schema:
                    manifest.config_schema = dynamic_schema
                else:
                    # Слияние свойств (properties)
                    existing_props = manifest.config_schema.get("properties") or {}
                    dynamic_props = dynamic_schema.get("properties") or {}
                    
                    # Глубокое слияние не требуется, так как это плоская структура параметров
                    merged_props = {**existing_props, **dynamic_props}
                    manifest.config_schema["properties"] = merged_props
                    
                    # Можно также объединять другие поля схемы (required и т.д.) если нужно
                    if "required" in dynamic_schema:
                        existing_req = manifest.config_schema.get("required") or []
                        manifest.config_schema["required"] = list(set(existing_req + dynamic_schema["required"]))

        # ── Hooks: lifecycle hooks ───────────────────────────────────
        on_enable = manifest.hooks.get("on_enable")
        if on_enable:
            _call_hook(on_enable, ctx)

    _log.info(
        "Loaded %d modules (%d enabled)",
        len(sorted_manifests),
        sum(1 for v in enabled_by_id.values() if v),
    )
