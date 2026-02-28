"""Топологическая сортировка модулей по зависимостям."""
from __future__ import annotations

import logging
from typing import Sequence

from backend.core.plugin.manifest import ModuleManifest

_log = logging.getLogger("nms.plugin.resolver")


def toposort_modules(manifests: Sequence[ModuleManifest]) -> list[ModuleManifest]:
    """Отсортировать модули так, чтобы зависимости шли раньше зависимых.

    При обнаружении цикла — возвращает исходный порядок с предупреждением.
    """
    items = list(manifests)
    by_id = {m.id: m for m in items}

    # Фильтруем зависимости — только известные id, но логируем отсутствующие
    deps_map = {}
    for m in items:
        valid_deps = []
        for d in m.deps:
            if d in by_id:
                valid_deps.append(d)
            else:
                _log.warning("Module %s declares unknown dependency: %s", m.id, d)
        deps_map[m.id] = valid_deps

    indegree = {m.id: len(deps_map[m.id]) for m in items}

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
