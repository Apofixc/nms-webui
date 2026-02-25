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

    def to_route_dict(self) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        if self.title:
            meta["title"] = self.title
        if self.icon:
            meta["icon"] = self.icon
        if self.submodule:
            meta["submodule"] = self.submodule
        return {
            "path": self.path,
            "name": self.name,
            "meta": meta,
        }


def parse_views_from_manifest(data: dict[str, Any]) -> list[UIViewDefinition]:
    routes = data.get("routes")
    if not isinstance(routes, list):
        return []
    out: list[UIViewDefinition] = []
    for row in routes:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path") or "").strip()
        name = str(row.get("name") or "").strip()
        if not path or not name:
            continue
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        out.append(
            UIViewDefinition(
                path=path,
                name=name,
                title=str(meta.get("title")) if meta.get("title") else None,
                icon=str(meta.get("icon")) if meta.get("icon") else None,
                submodule=str(row.get("submodule")) if row.get("submodule") else None,
            )
        )
    return out
