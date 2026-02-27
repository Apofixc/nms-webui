from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import yaml

try:  # Опциональная строгая проверка схемы
    import jsonschema
except Exception:  # pragma: no cover - отсутствие зависимости не фатально
    jsonschema = None

from backend.modules.stream.core.contract import IStreamBackend


def _default_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["meta", "capabilities"],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["name", "entry_point"],
                "properties": {
                    "name": {"type": "string"},
                    "version": {"type": "string"},
                    "entry_point": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
            },
            "capabilities": {
                "type": "object",
                "properties": {
                    "protocols": {"type": "array", "items": {"type": "string"}},
                    "outputs": {"type": "array", "items": {"type": "string"}},
                    "features": {"type": "array", "items": {"type": "string"}},
                    "priority_matrix": {"type": "object"},
                },
            },
            "resources": {"type": "object"},
            "config_schema": {"type": "object"},
        },
    }


@dataclass
class LoadedBackend:
    name: str
    cls: type[IStreamBackend]
    manifest: dict[str, Any]


class ModuleLoader:
    """Загрузчик субмодулей stream по manifest.yaml."""

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
        self._cache: dict[str, LoadedBackend] | None = None
        self._schema: dict[str, Any] | None = None

    def _get_schema(self) -> dict[str, Any]:
        if self._schema is not None:
            return self._schema
        schema_path = self.base_dir / "manifest_schema.json"
        if schema_path.exists():
            try:
                import json

                self._schema = json.loads(schema_path.read_text())
                return self._schema
            except Exception:
                pass
        self._schema = _default_schema()
        return self._schema

    def _validate_manifest(self, manifest: dict[str, Any]) -> None:
        if jsonschema is not None:
            schema = self._get_schema()
            jsonschema.validate(manifest, schema)  # type: ignore[attr-defined]
            return
        # Статическая минимальная проверка
        meta = manifest.get("meta") or {}
        if "name" not in meta or "entry_point" not in meta:
            raise ValueError("manifest.meta.name and manifest.meta.entry_point are required")
        if "capabilities" not in manifest:
            raise ValueError("manifest.capabilities is required")

    def _load_module(self, path: Path, module_name: str) -> ModuleType:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[arg-type]
        return module

    def _load_backend_class(self, subdir: Path, entry_point: str) -> type[IStreamBackend]:
        if ":" in entry_point:
            module_part, class_name = entry_point.split(":", 1)
        else:
            module_part, class_name = entry_point, "Backend"
        module_path = subdir / f"{module_part}.py"
        module = self._load_module(module_path, f"stream.{subdir.name}.{module_part}")
        backend_cls = getattr(module, class_name, None)
        if backend_cls is None:
            raise ImportError(f"Class {class_name} not found in {module_path}")
        if not issubclass(backend_cls, IStreamBackend):
            raise TypeError(f"{class_name} must implement IStreamBackend")
        return backend_cls

    def _iter_manifests(self):
        submodules_root = self.base_dir / "submodules"
        if not submodules_root.exists():
            return
        for child in submodules_root.iterdir():
            if not child.is_dir():
                continue
            manifest_path = child / "manifest.yaml"
            if manifest_path.exists():
                yield child, manifest_path

    def load(self) -> dict[str, type[IStreamBackend]]:
        if self._cache is not None:
            return {name: rec.cls for name, rec in self._cache.items()}

        registry: dict[str, LoadedBackend] = {}
        for subdir, manifest_path in self._iter_manifests():
            manifest = yaml.safe_load(manifest_path.read_text()) or {}
            try:
                self._validate_manifest(manifest)
            except Exception:
                # Legacy/foreign manifest without required fields — пропускаем
                continue
            meta = manifest.get("meta") or {}
            enabled = meta.get("enabled", True)
            if not enabled:
                continue
            name = meta.get("name") or subdir.name
            entry_point = meta.get("entry_point")
            backend_cls = self._load_backend_class(subdir, entry_point)
            registry[name] = LoadedBackend(name=name, cls=backend_cls, manifest=manifest)

        self._cache = registry
        return {name: rec.cls for name, rec in registry.items()}

    def manifests(self) -> dict[str, dict[str, Any]]:
        self.load()
        return {name: rec.manifest for name, rec in (self._cache or {}).items()}

    def invalidate_cache(self) -> None:
        self._cache = None


_default_loader = ModuleLoader()


def get_loader() -> ModuleLoader:
    return _default_loader
