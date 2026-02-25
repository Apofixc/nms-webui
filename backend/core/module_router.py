"""Инфраструктура модульных роутеров для backend WebUI."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from copy import deepcopy
import importlib
import logging
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml
from fastapi import APIRouter, FastAPI

from backend.core.module_state import is_module_enabled

RouterFactory = Callable[[], APIRouter]

_MODULE_ROUTERS: Dict[str, RouterFactory] = {}
_log = logging.getLogger("nms.modules")


@dataclass(frozen=True)
class ModuleContext:
    module_id: str
    root: Path
    manifest: dict[str, Any]
    parent_module_id: str | None = None
    is_submodule: bool = False


@dataclass(frozen=True)
class ModuleManifest:
    module_id: str
    name: str | None
    version: str | None
    enabled_by_default: bool
    deps: list[str]
    entrypoints: dict[str, Any]
    hooks: dict[str, str]
    assets: dict[str, Any]
    config_schema: str | None
    root: Path
    parent_module_id: str | None
    is_submodule: bool


def register_module_router(module_id: str, factory: RouterFactory) -> None:
    _MODULE_ROUTERS[module_id] = factory


def list_registered_routers() -> dict[str, str]:
    return {module_id: factory.__name__ for module_id, factory in _MODULE_ROUTERS.items()}


def _safe_load_yaml(path: Path) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        _log.warning("Failed to read manifest %s: %s", path, exc)
        return None
    if not isinstance(data, dict):
        _log.warning("Manifest %s must be a mapping", path)
        return None
    return data


def _parse_manifest(path: Path, parent_module_id: str | None = None, is_submodule: bool = False) -> ModuleManifest | None:
    data = _safe_load_yaml(path)
    if data is None:
        return None
    raw_module_id = str(data.get("id") or path.parent.name)
    module_id = f"{parent_module_id}.{raw_module_id}" if parent_module_id and "." not in raw_module_id else raw_module_id
    name = data.get("name")
    version = data.get("version")
    enabled_by_default = bool(data.get("enabled_by_default", True))
    deps = data.get("deps") or []
    if not isinstance(deps, list):
        deps = [deps]
    deps = [str(d) for d in deps if d]
    if parent_module_id and parent_module_id not in deps:
        deps.append(parent_module_id)
    entrypoints = data.get("entrypoints") or {}
    hooks = data.get("hooks") or {}
    assets = data.get("assets") or {}
    config_schema = data.get("config_schema")
    if not isinstance(entrypoints, dict):
        entrypoints = {}
    if not isinstance(hooks, dict):
        hooks = {}
    if not isinstance(assets, dict):
        assets = {}
    return ModuleManifest(
        module_id=module_id,
        name=str(name) if name else None,
        version=str(version) if version else None,
        enabled_by_default=enabled_by_default,
        deps=deps,
        entrypoints=entrypoints,
        hooks={str(k): str(v) for k, v in hooks.items() if v},
        assets=assets,
        config_schema=str(config_schema) if config_schema else None,
        root=path.parent,
        parent_module_id=parent_module_id,
        is_submodule=is_submodule,
    )


def _discover_manifests(modules_dir: Path) -> list[ModuleManifest]:
    if not modules_dir.exists():
        return []
    manifests: list[ModuleManifest] = []

    def _walk_submodules(parent_dir: Path, parent_module_id: str) -> None:
        submodules_dir = parent_dir / "submodules"
        if not submodules_dir.exists():
            return
        for submodule_dir in sorted([p for p in submodules_dir.iterdir() if p.is_dir()]):
            sub_manifest_path = next(iter(sorted(submodule_dir.glob("manifest.y*ml"))), None)
            if sub_manifest_path is None:
                continue
            sub_manifest = _parse_manifest(
                sub_manifest_path,
                parent_module_id=parent_module_id,
                is_submodule=True,
            )
            if sub_manifest is None:
                continue
            manifests.append(sub_manifest)
            _walk_submodules(submodule_dir, sub_manifest.module_id)

    for module_dir in sorted([p for p in modules_dir.iterdir() if p.is_dir()]):
        path = next(iter(sorted(module_dir.glob("manifest.y*ml"))), None)
        if path is None:
            continue
        manifest = _parse_manifest(path)
        if manifest is None:
            continue
        manifests.append(manifest)
        _walk_submodules(module_dir, manifest.module_id)
    return manifests


def _toposort_manifests(manifests: Iterable[ModuleManifest]) -> list[ModuleManifest]:
    items = list(manifests)
    by_id = {m.module_id: m for m in items}
    deps_map = {m.module_id: [d for d in m.deps if d in by_id] for m in items}
    indegree = {m.module_id: 0 for m in items}
    for module_id, deps in deps_map.items():
        indegree[module_id] = len(deps)
    ready = [mid for mid, deg in indegree.items() if deg == 0]
    order: list[ModuleManifest] = []
    while ready:
        mid = ready.pop(0)
        order.append(by_id[mid])
        for dependent, deps in deps_map.items():
            if mid not in deps:
                continue
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if len(order) != len(items):
        _log.warning("Module dependency cycle detected; loading in discovery order")
        return items
    return order


def _import_from_path(path: str) -> Any:
    module_path, sep, attr = path.partition(":")
    if not module_path:
        raise ValueError("entrypoint path is empty")
    mod = importlib.import_module(module_path)
    return getattr(mod, attr) if sep else mod


def _call_with_fallbacks(callable_obj: Callable[..., Any], *args: Any) -> Any:
    try:
        return callable_obj(*args)
    except TypeError:
        try:
            return callable_obj(*args[:1])
        except TypeError:
            return callable_obj()


def _load_router_entrypoint(entrypoint: str, app: FastAPI, ctx: ModuleContext) -> None:
    try:
        factory = _import_from_path(entrypoint)
        router = _call_with_fallbacks(factory, ctx)
        if not isinstance(router, APIRouter):
            raise TypeError("router factory must return APIRouter")
        app.include_router(router)
        _log.info("Module %s: router registered", ctx.module_id)
    except Exception as exc:
        _log.warning("Module %s: router entrypoint failed (%s)", ctx.module_id, exc)


def _load_service_entrypoint(entrypoint: str, app: FastAPI, ctx: ModuleContext) -> None:
    try:
        registrar = _import_from_path(entrypoint)
        _call_with_fallbacks(registrar, app, ctx)
        _log.info("Module %s: services registered", ctx.module_id)
    except Exception as exc:
        _log.warning("Module %s: service entrypoint failed (%s)", ctx.module_id, exc)


def _call_hook(entrypoint: str, ctx: ModuleContext) -> None:
    try:
        hook = _import_from_path(entrypoint)
        _call_with_fallbacks(hook, ctx)
        _log.info("Module %s: hook executed", ctx.module_id)
    except Exception as exc:
        _log.warning("Module %s: hook failed (%s)", ctx.module_id, exc)


def load_module_routers(app: FastAPI, modules_dir: Path | None = None) -> None:
    if modules_dir is None:
        modules_dir = Path(__file__).resolve().parent.parent / "modules"
    manifests = _toposort_manifests(_discover_manifests(modules_dir))
    enabled_by_id: dict[str, bool] = {}
    for manifest in manifests:
        parent_enabled = True
        if manifest.parent_module_id:
            parent_enabled = enabled_by_id.get(manifest.parent_module_id, True)
        if not parent_enabled:
            enabled_by_id[manifest.module_id] = False
            _log.info("Submodule %s skipped because parent %s is disabled", manifest.module_id, manifest.parent_module_id)
            continue
        enabled = is_module_enabled(manifest.module_id, default=manifest.enabled_by_default)
        enabled_by_id[manifest.module_id] = enabled
        if not enabled:
            _log.info("Module %s disabled; skipping", manifest.module_id)
            continue
        ctx = ModuleContext(module_id=manifest.module_id, root=manifest.root, manifest=deepcopy({
            "id": manifest.module_id,
            "name": manifest.name,
            "version": manifest.version,
            "deps": manifest.deps,
            "entrypoints": manifest.entrypoints,
            "hooks": manifest.hooks,
            "assets": manifest.assets,
            "config_schema": manifest.config_schema,
            "parent_module_id": manifest.parent_module_id,
            "is_submodule": manifest.is_submodule,
        }), parent_module_id=manifest.parent_module_id, is_submodule=manifest.is_submodule)
        entrypoints = manifest.entrypoints or {}
        router_entry = entrypoints.get("router")
        if isinstance(router_entry, list):
            for ep in router_entry:
                if ep:
                    _load_router_entrypoint(str(ep), app, ctx)
        elif router_entry:
            _load_router_entrypoint(str(router_entry), app, ctx)
        service_entries = entrypoints.get("services") or []
        if isinstance(service_entries, (str, bytes)):
            service_entries = [service_entries]
        if isinstance(service_entries, list):
            for ep in service_entries:
                if ep:
                    _load_service_entrypoint(str(ep), app, ctx)
        hook_entry = manifest.hooks.get("on_enable") if manifest.hooks else None
        if hook_entry:
            _call_hook(hook_entry, ctx)
    for module_id, factory in _MODULE_ROUTERS.items():
        if not is_module_enabled(module_id, default=True):
            continue
        try:
            router = factory()
            app.include_router(router)
        except Exception as exc:
            _log.warning("Legacy router %s failed (%s)", module_id, exc)
