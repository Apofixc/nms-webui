"""Ядро модуля stream: лёгкий init без тяжёлых зависимостей (astra/httpx и т.п.)."""
from . import pipeline, types
from .contract import IStreamBackend
from .exceptions import BackendInitializationError, BackendProcessError, NoBackendFound
from .loader import ModuleLoader, get_loader
from .router import BackendCandidate, choose_backend, find_candidates
from .worker_pool import WorkerPool, get_pool

__all__ = [
    "types",
    "pipeline",
    "WorkerPool",
    "get_pool",
    "IStreamBackend",
    "BackendInitializationError",
    "BackendProcessError",
    "NoBackendFound",
    "ModuleLoader",
    "get_loader",
    "BackendCandidate",
    "choose_backend",
    "find_candidates",
]
