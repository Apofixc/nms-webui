# Проверка здоровья бэкендов стриминга
import asyncio
import logging
import os
import shutil
from typing import Dict, Optional

from backend.modules.stream.core.contract import IStreamBackend

logger = logging.getLogger(__name__)

# Стандартные бинарники для проверки
DEFAULT_BINARIES = {
    "ffmpeg": "ffmpeg",
    "vlc": "cvlc",
    "gstreamer": "gst-launch-1.0",
    "tsduck": "tsp",
    "astra": "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182",
}


async def check_backends_health(backends: Dict[str, IStreamBackend]) -> dict:
    """Проверка здоровья всех зарегистрированных бэкендов.

    Для каждого бэкенда выполняет:
    1. Проверку доступности (is_available).
    2. Расширенный health_check (версия, путь, активные сессии).

    Также проверяет наличие бинарников в PATH
    для бэкендов, которые не были загружены.
    """
    results = {}

    # Проверка загруженных бэкендов (параллельно)
    tasks = {}
    for backend_id, backend in backends.items():
        tasks[backend_id] = asyncio.create_task(_check_single_backend(backend))

    for backend_id, task in tasks.items():
        results[backend_id] = await task

    # Проверка незагруженных бинарников
    for binary_id, binary_path in DEFAULT_BINARIES.items():
        if binary_id not in results:
            exists = _check_binary_exists(binary_path)
            results[binary_id] = {
                "available": False,
                "loaded": False,
                "binary_exists": exists,
                "binary_path": binary_path,
                "details": {},
                "error": "Бэкенд не загружен" if exists else "Бинарник не найден",
            }

    total = len(results)
    available = sum(1 for r in results.values() if r.get("available", False))

    return {
        "total": total,
        "available": available,
        "unavailable": total - available,
        "backends": results,
    }


async def _check_single_backend(backend: IStreamBackend) -> dict:
    """Проверка одного бэкенда."""
    try:
        available = await backend.is_available()
        health = await backend.health_check()
        return {
            "available": available,
            "loaded": True,
            "capabilities": [c.value for c in backend.capabilities],
            "details": health,
            "error": None,
        }
    except Exception as e:
        logger.warning(f"Health check для '{backend.backend_id}' не прошел: {e}")
        return {
            "available": False,
            "loaded": True,
            "capabilities": [c.value for c in backend.capabilities],
            "details": {},
            "error": str(e),
        }


def _check_binary_exists(path: str) -> bool:
    """Проверка наличия бинарника в системе."""
    if shutil.which(path):
        return True
    return os.path.isfile(path) and os.access(path, os.X_OK)


async def quick_health_summary(backends: Dict[str, IStreamBackend]) -> dict:
    """Быстрая сводка здоровья (без детализации)."""
    summary = {}
    for bid, backend in backends.items():
        try:
            summary[bid] = await backend.is_available()
        except Exception:
            summary[bid] = False
    return summary
