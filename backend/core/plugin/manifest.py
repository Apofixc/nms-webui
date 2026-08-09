"""Pydantic-схема manifest.yaml модуля."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from backend.core.exceptions import ModuleValidationError


class RouteMetaSchema(BaseModel):
    """Meta-данные для UI-маршрута."""
    title: str | None = None
    icon: str | None = None
    group: str | None = None
    requires_auth: bool = False
    permissions: list[str] = Field(default_factory=list)
    settings_view: bool = False
    module_id: str | None = None
    submodule: str | None = None


class RouteSchema(BaseModel):
    """Определение UI-маршрута модуля."""
    path: str
    name: str
    meta: RouteMetaSchema = Field(default_factory=RouteMetaSchema)


class MenuItemSchema(BaseModel):
    """Пункт меню."""
    path: str
    label: str
    icon: str | None = None


class MenuSchema(BaseModel):
    """Конфигурация меню модуля."""
    location: str | None = None  # "sidebar" | "footer" | None
    group: str | None = None
    items: list[MenuItemSchema] = Field(default_factory=list)


def _validate_entrypoint_str(v: str) -> None:
    if not isinstance(v, str) or ":" not in v:
        raise ModuleValidationError(f"entrypoint format must be 'pkg.mod:attr', got '{v}'")
    mod, _, attr = v.partition(":")
    if not mod.strip() or not attr.strip():
        raise ModuleValidationError(f"entrypoint format must be 'pkg.mod:attr', got '{v}'")


class EntrypointsSchema(BaseModel):
    """Точки входа модуля."""
    factory: str | None = None
    router: str | list[str] | None = None
    services: str | list[str] | None = None
    settings: str | None = None

    @field_validator("factory", "settings", mode="after")
    @classmethod
    def validate_single_ep(cls, v: str | None) -> str | None:
        if v is not None:
            _validate_entrypoint_str(v)
        return v

    @field_validator("router", "services", mode="after")
    @classmethod
    def validate_list_or_single_ep(cls, v: str | list[str] | None) -> str | list[str] | None:
        if v is None:
            return v
        if isinstance(v, str):
            _validate_entrypoint_str(v)
        elif isinstance(v, list):
            for item in v:
                _validate_entrypoint_str(item)
        return v


class AssetsSchema(BaseModel):
    """Ресурсы модуля."""
    cache_dirs: list[str] = Field(default_factory=list)
    data_dirs: list[str] = Field(default_factory=list)


class PermissionSchema(BaseModel):
    """Определение разрешения, предоставляемого модулем."""
    id: str
    name: str
    category: str | None = None
    description: str | None = ""


class WidgetSchema(BaseModel):
    """Схема виджета модуля для Dashboard."""
    id: str
    title: str = ""
    description: str = ""
    component: str = ""
    endpoint: str | None = None
    stream_endpoint: str | None = None
    size: Literal["small", "medium", "large"] = "medium"
    refresh_interval: int | None = None
    type: str = "summary"
    default_active: bool = False
    resizable: bool = True
    view_permission: str | None = None
    control_permission: str | None = None


class ModuleManifest(BaseModel):
    """Pydantic-модель manifest.yaml модуля.

    Single source of truth для каждого модуля/подмодуля.
    """
    manifest_version: int = 1
    id: str
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    enabled_by_default: bool = True
    type: Literal["system", "feature", "driver"] = "feature"

    # Зависимости
    deps: list[str] = Field(default_factory=list)
    optional_deps: list[str] = Field(default_factory=list)

    # Субмодуль?
    parent: str | None = None

    # Точки входа
    entrypoints: EntrypointsSchema = Field(default_factory=EntrypointsSchema)

    # UI, разрешения и виджеты
    routes: list[RouteSchema] = Field(default_factory=list)
    menu: MenuSchema = Field(default_factory=MenuSchema)
    permissions: list[PermissionSchema] = Field(default_factory=list)
    widgets: list[WidgetSchema] = Field(default_factory=list)

    # Настройки (JSON Schema)
    config_schema: dict[str, Any] | None = None

    # Совместимость с версиями ядра
    min_core_version: str | None = None
    max_core_version: str | None = None

    # Lifecycle hooks и ресурсы
    hooks: dict[Literal["install", "uninstall", "on_enable", "on_disable"], str] = Field(default_factory=dict)
    assets: AssetsSchema = Field(default_factory=AssetsSchema)

    @field_validator("parent")
    @classmethod
    def validate_parent(cls, v: str | None) -> str | None:
        if v is not None and "." in v:
            raise ModuleValidationError("parent не может содержать точку (нельзя ссылаться на субмодуль)")
        return v

    def to_api_dict(self) -> dict[str, Any]:
        """Сериализация для API-ответов."""
        return {
            "manifest_version": self.manifest_version,
            "id": self.id,
            "name": self.name or self.id,
            "version": self.version,
            "description": self.description,
            "enabled_by_default": self.enabled_by_default,
            "type": self.type,
            "min_core_version": self.min_core_version,
            "max_core_version": self.max_core_version,
            "deps": self.deps,
            "optional_deps": self.optional_deps,
            "parent": self.parent,
            "is_submodule": self.parent is not None,
            "parent_id": self.parent,
            "permissions": [p.model_dump() for p in self.permissions],
            "widgets": [w.model_dump() for w in self.widgets],
            "routes": [
                {"path": r.path, "name": r.name, "meta": r.meta.model_dump(exclude_none=True)}
                for r in self.routes
            ],
            "menu": {
                "location": self.menu.location,
                "group": self.menu.group,
                "items": [{"path": i.path, "label": i.label, "icon": i.icon} for i in self.menu.items],
            } if self.menu.location or self.menu.items else None,
            "config_schema": self.config_schema,
        }



