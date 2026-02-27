from __future__ import annotations

from typing import Iterable, Optional, Sequence

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.exceptions import NoBackendFound
from backend.modules.stream.core.loader import ModuleLoader, get_loader
from backend.modules.stream.core.types import StreamTask


class BackendCandidate:
    def __init__(self, name: str, backend_cls: type[IStreamBackend], score: int, priority: int):
        self.name = name
        self.backend_cls = backend_cls
        self.score = score
        self.priority = priority

    def sort_key(self) -> tuple[int, int, str]:
        # Сначала score (desc), затем priority (desc), затем имя — стабильный порядок
        return (self.score, self.priority, self.name)


def _priority_from_caps(caps: dict, input_proto: str, output_format: str) -> int:
    matrix = (caps or {}).get("priority_matrix") or {}
    pr = (matrix.get(input_proto) or {}).get(output_format)
    return int(pr) if pr is not None else 0


def _supports_features(caps: dict, required: Iterable[str] | None) -> bool:
    if not required:
        return True
    features = set((caps or {}).get("features") or [])
    return set(required).issubset(features)


def find_candidates(
    task: StreamTask,
    *,
    required_features: Optional[Sequence[str]] = None,
    loader: ModuleLoader | None = None,
) -> list[BackendCandidate]:
    loader = loader or get_loader()
    registry = loader.load()
    manifests = loader.manifests()
    candidates: list[BackendCandidate] = []
    for name, backend_cls in registry.items():
        manifest_caps = (manifests.get(name) or {}).get("capabilities") or {}
        if not _supports_features(manifest_caps, required_features):
            continue
        backend = backend_cls()
        score = backend.match_score(task.input_protocol, task.output_format)
        if score <= 0:
            continue
        prio = _priority_from_caps(manifest_caps, task.input_protocol, task.output_format)
        candidates.append(BackendCandidate(name, backend_cls, score, prio))
    return candidates


def choose_backend(
    task: StreamTask,
    *,
    required_features: Optional[Sequence[str]] = None,
    loader: ModuleLoader | None = None,
) -> type[IStreamBackend]:
    candidates = find_candidates(task, required_features=required_features, loader=loader)
    if not candidates:
        raise NoBackendFound(f"No backend for {task.input_protocol}->{task.output_format}")
    candidates.sort(key=lambda c: c.sort_key(), reverse=True)
    return candidates[0].backend_cls


__all__ = ["choose_backend", "find_candidates", "BackendCandidate"]
