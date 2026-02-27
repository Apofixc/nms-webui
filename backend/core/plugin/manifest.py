"""Pydantic-схема manifest.yaml модуля."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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


class EntrypointsSchema(BaseModel):
    """Точки входа модуля."""
    factory: str | None = None
    router: str | list[str] | None = None
    services: str | list[str] | None = None
    settings: str | None = None


class AssetsSchema(BaseModel):
    """Ресурсы модуля."""
    cache_dirs: list[str] = Field(default_factory=list)
    data_dirs: list[str] = Field(default_factory=list)


class ModuleManifest(BaseModel):
    """Pydantic-модель manifest.yaml модуля.

    Single source of truth для каждого модуля/подмодуля.
    """
    id: str
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    enabled_by_default: bool = True
    type: str = "feature"  # "system" | "feature" | "driver"

    # Зависимости
    deps: list[str] = Field(default_factory=list)

    # Субмодуль?
    parent: str | None = None

    # Точки входа
    entrypoints: EntrypointsSchema = Field(default_factory=EntrypointsSchema)

    # UI
    routes: list[RouteSchema] = Field(default_factory=list)
    menu: MenuSchema = Field(default_factory=MenuSchema)

    # Настройки (JSON Schema)
    config_schema: dict[str, Any] | None = None

    # Lifecycle hooks и ресурсы
    hooks: dict[str, str] = Field(default_factory=dict)
    assets: AssetsSchema = Field(default_factory=AssetsSchema)

    def to_api_dict(self) -> dict[str, Any]:
        """Сериализация для API-ответов."""
        return {
            "id": self.id,
            "name": self.name or self.id,
            "version": self.version,
            "description": self.description,
            "enabled_by_default": self.enabled_by_default,
            "type": self.type,
            "deps": self.deps,
            "parent": self.parent,
            "is_submodule": self.parent is not None,
            "parent_id": self.parent,
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
