"""Typed UI definitions derived from module manifests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UIViewDefinition:
    """Physical UI view object used by registry/API and unit tests."""

    path: str
    name: str
    title: str | None = None
    icon: str | None = None
    submodule: str | None = None
    module_id: str | None = None

    def to_route_dict(self) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        if self.title:
            meta["title"] = self.title
        if self.icon:
            meta["icon"] = self.icon
        if self.submodule:
            meta["submodule"] = self.submodule
        if self.module_id:
            meta["module_id"] = self.module_id
        return {
            "path": self.path,
            "name": self.name,
            "meta": meta,
        }


def parse_views_from_manifest(data: dict[str, Any]) -> list[dict[str, Any]]:
    routes = data.get("routes")
    if not isinstance(routes, list):
        return []
    out: list[dict[str, Any]] = []
    for row in routes:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path") or "").strip()
        name = str(row.get("name") or "").strip()
        if not path or not name:
            continue
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        # Create route dict with all meta fields
        route_dict = {
            "path": path,
            "name": name,
            "meta": meta.copy(),  # Copy all meta fields
        }
        out.append(route_dict)
    return out
