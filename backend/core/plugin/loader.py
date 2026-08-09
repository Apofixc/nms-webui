"""Сканер и загрузчик модулей по manifest.yaml."""
from __future__ import annotations

import importlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, FastAPI

from backend.core.exceptions import ModuleValidationError
from backend.core.plugin.context import ModuleContext
from backend.core.plugin.manifest import ModuleManifest
from backend.core.plugin.registry import is_module_enabled
from backend.core.plugin.resolver import toposort_modules

_log = logging.getLogger("nms.plugin.loader")

CORE_VERSION = "1.0.0"


def _parse_semver(v_str: str) -> tuple[int, ...]:
    """Преобразовать строку версии '1.2.3' в кортеж чисел (1, 2, 3)."""
    try:
        clean = v_str.strip().lstrip("v")
        parts = [int(x) for x in clean.split(".") if x.isdigit()]
        return tuple(parts) if parts else (0,)
    except Exception:
        return (0,)


def is_version_compatible(min_version: str | None, max_version: str | None, current: str = CORE_VERSION) -> bool:
    """Проверить совместимость версии ядра с требованиями модуля."""
    curr_t = _parse_semver(current)
    if min_version:
        if curr_t < _parse_semver(min_version):
            return False
    if max_version:
        if curr_t > _parse_semver(max_version):
            return False
    return True


def run_bash_script_hook(script_relative_path: str, ctx: ModuleContext, action_name: str = "hook") -> bool:
    """Выполнить bash-скрипт модуля (install.sh / uninstall.sh)."""
    import os
    import subprocess

    script_path = ctx.root / script_relative_path
    if not script_path.exists() or not script_path.is_file():
        return True

    try:
        os.chmod(script_path, 0o755)
    except Exception:
        pass

    project_root = ctx.root.resolve().parent.parent
    env = {
        **os.environ,
        "MODULE_ID": ctx.module_id,
        "MODULE_ROOT": str(ctx.root),
        "MODULE_DATA_DIR": str(ctx.get_data_dir()),
        "PROJECT_ROOT": str(project_root),
    }

    try:
        _log.info("Module %s: running %s script (%s)", ctx.module_id, action_name, script_path)
        result = subprocess.run(["bash", str(script_path)], env=env, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            _log.warning("Module %s: %s script failed (code %d): %s", ctx.module_id, action_name, result.returncode, result.stderr)
            return False
        _log.info("Module %s: %s script succeeded", ctx.module_id, action_name)
        return True
    except Exception as exc:
        _log.warning("Module %s: failed to execute %s script: %s", ctx.module_id, action_name, exc)
        return False



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
    """Сканирует modules/ и возвращает все manifest.yaml (однослойные субмодули)."""
    if not modules_dir.exists():
        _log.info("Modules directory %s does not exist — no modules to load", modules_dir)
        return []

    manifests: list[ModuleManifest] = []

    for module_dir in sorted(p for p in modules_dir.iterdir() if p.is_dir()):
        manifest_path = next(iter(sorted(module_dir.glob("manifest.y*ml"))), None)
        if manifest_path is None:
            continue
        manifest = _parse_manifest(manifest_path)
        if manifest is None:
            continue
        manifests.append(manifest)

        submodules_dir = module_dir / "submodules"
        if submodules_dir.exists() and submodules_dir.is_dir():
            for sub_dir in sorted(p for p in submodules_dir.iterdir() if p.is_dir()):
                sub_id = f"{manifest.id}.{sub_dir.name}"
                if (sub_dir / "submodules").exists():
                    from backend.core.plugin.registry import register_module_error
                    register_module_error(sub_id, "вложенные субмодули запрещены")
                    _log.warning("Module %s skipped: nested submodules are not allowed", sub_id)
                    continue

                sub_manifest_path = next(iter(sorted(sub_dir.glob("manifest.y*ml"))), None)
                if sub_manifest_path is None:
                    continue
                sub_manifest = _parse_manifest(sub_manifest_path, parent_id=manifest.id)
                if sub_manifest is None:
                    continue
                manifests.append(sub_manifest)

    return manifests


def _import_from_path(dotted_path: str) -> Any:
    """Импортировать объект по 'module.path:attribute'."""
    module_path, sep, attr = dotted_path.partition(":")
    if not module_path:
        raise ModuleValidationError("entrypoint path is empty")
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
            raise ModuleValidationError("router factory must return APIRouter")
        app.include_router(router)
        _log.info("Module %s: router registered via %s", ctx.module_id, entrypoint)
    except Exception as exc:
        _log.warning("Module %s: router entrypoint failed (%s)", ctx.module_id, exc)
        from backend.core.plugin.registry import register_module_error
        register_module_error(ctx.module_id, f"Ошибка роутера ({entrypoint}): {exc}")


def _load_service(entrypoint: str, app: FastAPI, ctx: ModuleContext) -> None:
    """Зарегистрировать сервис модуля."""
    try:
        registrar = _import_from_path(entrypoint)
        _call_with_fallbacks(registrar, app, ctx)
        _log.info("Module %s: service registered via %s", ctx.module_id, entrypoint)
    except Exception as exc:
        _log.warning("Module %s: service entrypoint failed (%s)", ctx.module_id, exc)
        from backend.core.plugin.registry import register_module_error
        register_module_error(ctx.module_id, f"Ошибка сервиса ({entrypoint}): {exc}")


def _call_hook(entrypoint: str, ctx: ModuleContext) -> None:
    """Вызвать lifecycle hook."""
    try:
        hook = _import_from_path(entrypoint)
        _call_with_fallbacks(hook, ctx)
        _log.info("Module %s: hook executed (%s)", ctx.module_id, entrypoint)
    except Exception as exc:
        _log.warning("Module %s: hook failed (%s)", ctx.module_id, exc)
        from backend.core.plugin.registry import register_module_error
        register_module_error(ctx.module_id, f"Ошибка хука ({entrypoint}): {exc}")


def _load_factory(entrypoint: str, ctx: ModuleContext) -> Any | None:
    """Создать экземпляр модуля через factory entrypoint."""
    try:
        factory_fn = _import_from_path(entrypoint)
        instance = _call_with_fallbacks(factory_fn, ctx)
        _log.info("Module %s: instance created via %s", ctx.module_id, entrypoint)
        return instance
    except Exception as exc:
        _log.warning("Module %s: factory failed (%s)", ctx.module_id, exc)
        from backend.core.plugin.registry import register_module_error
        register_module_error(ctx.module_id, f"Ошибка фабрики ({entrypoint}): {exc}")
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


def _load_single_manifest(manifest: ModuleManifest, app: FastAPI, modules_dir: Path) -> None:
    """Загрузить точки входа, роутеры и инстанс для одного модуля."""
    from backend.core.plugin.registry import register_instance, register_module_error, clear_module_error

    clear_module_error(manifest.id)

    if not is_version_compatible(manifest.min_core_version, manifest.max_core_version):
        err = f"Несовместимая версия ядра {CORE_VERSION} (требуется min: {manifest.min_core_version}, max: {manifest.max_core_version})"
        _log.warning("Module %s skipped: %s", manifest.id, err)
        register_module_error(manifest.id, err)
        return

    ctx = ModuleContext(
        module_id=manifest.id,
        root=modules_dir / manifest.id.split(".")[0],
        manifest=manifest.to_api_dict(),
        parent_module_id=manifest.parent,
        is_submodule=manifest.parent is not None,
    )

    # ── Bash Hook: Выполнение install.sh при установке/первичной загрузке ──
    install_script = manifest.hooks.get("install") or "scripts/install.sh"
    run_bash_script_hook(install_script, ctx, action_name="install")

    # ── i18n: загрузка локализаций из папки locales/ ─────────────────────
    from backend.core.i18n import load_module_locales
    load_module_locales(ctx.root)

    # ── Factory: создание экземпляра модуля ──────────────────────
    ep = manifest.entrypoints
    instance = None
    if ep.factory:
        instance = _load_factory(str(ep.factory), ctx)
        if instance is not None:
            register_instance(manifest.id, instance)
            if hasattr(instance, "get_log_provider"):
                try:
                    lp = instance.get_log_provider()
                    if lp is not None:
                        from backend.core.log_providers import log_provider_registry
                        log_provider_registry.register(lp)
                        _log.info("Module %s: log provider registered (%s)", manifest.id, lp.id)
                except Exception as exc:
                    _log.warning("Module %s: log provider failed (%s)", manifest.id, exc)
            # Вызов lifecycle: init()
            if hasattr(instance, "init"):
                try:
                    import asyncio
                    if asyncio.iscoroutinefunction(instance.init):
                        try:
                            loop = asyncio.get_running_loop()
                            # Инициализация требует мгновенного завершения
                            loop.run_until_complete(instance.init())
                        except RuntimeError:
                            asyncio.run(instance.init())
                    else:
                        instance.init()
                    _log.info("Module %s: init() completed", manifest.id)
                except Exception as exc:
                    _log.warning("Module %s: init() failed (%s)", manifest.id, exc)
                    register_module_error(manifest.id, f"Ошибка init(): {exc}")
                    return  # Прерываем загрузку роутеров и сервисов при сбое init()

            # Вызов lifecycle: start() при динамической загрузке (если активен event loop)
            if hasattr(instance, "start"):
                try:
                    import asyncio
                    if asyncio.iscoroutinefunction(instance.start):
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(instance.start())
                            _log.info("Module %s: async start() scheduled", manifest.id)
                        except RuntimeError:
                            asyncio.run(instance.start())
                            _log.info("Module %s: async start() completed", manifest.id)
                    else:
                        try:
                            asyncio.get_running_loop()
                            instance.start()
                            _log.info("Module %s: start() completed", manifest.id)
                        except RuntimeError:
                            _log.debug("Module %s: start() deferred until event loop starts", manifest.id)
                except Exception as exc:
                    _log.warning("Module %s: start() failed (%s)", manifest.id, exc)
                    register_module_error(manifest.id, f"Ошибка start(): {exc}")

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
            if not manifest.config_schema:
                manifest.config_schema = dynamic_schema
            else:
                existing_props = manifest.config_schema.get("properties") or {}
                dynamic_props = dynamic_schema.get("properties") or {}
                manifest.config_schema["properties"] = {**existing_props, **dynamic_props}

    # ── Hooks: lifecycle hooks ───────────────────────────────────
    on_enable = manifest.hooks.get("on_enable")
    if on_enable:
        _call_hook(on_enable, ctx)

    from backend.core.bus import event_bus
    event_bus.publish("core.modules.loaded", {"module_id": manifest.id}, is_core=True)


async def unload_single_module_async(module_id: str) -> None:
    """Асинхронно остановить активные сервисы модуля и вызвать hook on_disable / uninstall.sh."""
    import asyncio
    from backend.core.plugin.registry import get_instance, get_manifest
    from backend.core.plugin.context import cleanup_module_events, cleanup_module_scheduler

    cleanup_module_events(module_id)
    cleanup_module_scheduler(module_id)

    inst = get_instance(module_id)
    if inst:
        try:
            if hasattr(inst, "stop"):
                if asyncio.iscoroutinefunction(inst.stop):
                    await inst.stop()
                else:
                    inst.stop()
                _log.info("Module %s stopped on unload", module_id)
        except Exception as exc:
            _log.warning("Module %s stop failed on unload: %s", module_id, exc)

    manifest = get_manifest(module_id)
    if manifest:
        modules_dir = Path(__file__).resolve().parent.parent.parent / "modules"
        ctx = ModuleContext(
            module_id=module_id,
            root=modules_dir / module_id.split(".")[0],
            manifest=manifest.to_api_dict()
        )
        uninstall_script = manifest.hooks.get("uninstall") or "scripts/uninstall.sh"
        run_bash_script_hook(uninstall_script, ctx, action_name="uninstall")

        if manifest.hooks.get("on_disable"):
            _call_hook(manifest.hooks["on_disable"], ctx)


def unload_single_module(module_id: str) -> None:
    """Остановить активные сервисы модуля и вызвать hook on_disable / uninstall.sh (синхронная обертка)."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(unload_single_module_async(module_id))
            return
    except RuntimeError:
        pass
    asyncio.run(unload_single_module_async(module_id))


def uninstall_module(module_id: str) -> None:
    """Останов и транзакционная очистка ВСЕХ сущностей модуля в единой БД nms.db и на диске."""
    import shutil
    from backend.core.database import get_db_connection
    from backend.core.plugin.registry import get_instance, unregister_manifest

    inst = get_instance(module_id)
    if inst:
        try:
            if hasattr(inst, "uninstall"):
                inst.uninstall()
                _log.info("Executed uninstall() hook for module %s", module_id)
        except Exception as exc:
            _log.warning("Module %s uninstall hook error: %s", module_id, exc)

    # 1. Остановка модуля
    unload_single_module(module_id)

    # 2. Атомарная транзакция очистки единой БД nms.db
    try:
        conn = get_db_connection()
        clean_id = module_id.replace("-", "_").replace(".", "_")
        prefix = f"mod_{clean_id}_"
        prefix_raw = f"mod_{module_id}_"

        with conn:
            # А) Таблицы модуля
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE ? OR name LIKE ?)",
                (f"{prefix}%", f"{prefix_raw}%"),
            )
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
                _log.info("Dropped module table: %s", table)



            # В) Разрешения модуля и связи с ролями
            conn.execute(
                """
                DELETE FROM role_permissions 
                WHERE permission_id IN (SELECT id FROM permissions WHERE module_id = ?)
                """,
                (module_id,),
            )
            conn.execute("DELETE FROM permissions WHERE module_id = ?", (module_id,))

            # Г) Настройки модуля
            conn.execute("DELETE FROM system_settings WHERE key = ?", (f"module_{module_id}_settings",))

        conn.close()
        _log.info("Successfully cleaned DB resources for module %s", module_id)
    except Exception as exc:
        _log.error("Failed DB cleanup for module %s: %s", module_id, exc)

    # 3. Удаление дисковых данных песочницы
    try:
        modules_dir = Path(__file__).resolve().parent.parent.parent / "modules"
        ctx = ModuleContext(module_id=module_id, root=modules_dir / module_id.split(".")[0])
        shutil.rmtree(ctx.get_data_dir(), ignore_errors=True)
        shutil.rmtree(ctx.get_cache_dir(), ignore_errors=True)
    except Exception as exc:
        _log.warning("Failed directory cleanup for module %s: %s", module_id, exc)

    # 4. Исключение из реестра
    unregister_manifest(module_id)




def scan_and_register_modules(app: FastAPI, modules_dir: Path | None = None) -> list[ModuleManifest]:
    """Сканирует директорию modules/, регистрирует новые найденные манифесты."""
    if modules_dir is None:
        modules_dir = Path(__file__).resolve().parent.parent.parent / "modules"

    raw = discover_manifests(modules_dir)
    if not raw:
        return []

    from backend.core.plugin.registry import register_manifest, get_manifest

    newly_found = []
    for manifest in raw:
        existing = get_manifest(manifest.id)
        enabled = is_module_enabled(manifest.id, default=manifest.enabled_by_default)
        register_manifest(manifest, enabled=enabled)
        if not existing and enabled:
            _load_single_manifest(manifest, app, modules_dir)
            newly_found.append(manifest)

    return raw


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
    from backend.core.plugin.registry import register_manifest

    enabled_by_id: dict[str, bool] = {}

    for manifest in sorted_manifests:
        deps_satisfied = True
        missing_dep = None
        for dep in manifest.deps:
            if not enabled_by_id.get(dep, False):
                deps_satisfied = False
                missing_dep = dep
                break

        enabled = is_module_enabled(manifest.id, default=manifest.enabled_by_default)

        if not deps_satisfied:
            enabled = False
            enabled_by_id[manifest.id] = False
            if manifest.parent == missing_dep:
                _log.info("Module %s skipped (parent %s disabled or missing)", manifest.id, missing_dep)
            else:
                _log.warning(
                    "Module %s cannot be enabled: dependency '%s' is missing or disabled",
                    manifest.id, missing_dep
                )
        else:
            enabled_by_id[manifest.id] = enabled

        for opt_dep in manifest.optional_deps:
            if not enabled_by_id.get(opt_dep, False):
                _log.info("Module %s: optional dependency '%s' is not active", manifest.id, opt_dep)

        register_manifest(manifest, enabled=enabled)

        if not enabled:
            if deps_satisfied:
                _log.info("Module %s disabled; skipping entrypoints", manifest.id)
            continue

        _load_single_manifest(manifest, app, modules_dir)

    _log.info(
        "Loaded %d modules (%d enabled)",
        len(sorted_manifests),
        sum(1 for v in enabled_by_id.values() if v),
    )

