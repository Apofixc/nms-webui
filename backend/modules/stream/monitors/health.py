# Проверка здоровья бэкендов стриминга
import logging
from typing import Dict

from backend.modules.stream.core.contract import IStreamBackend

logger = logging.getLogger(__name__)


async def check_backends_health(backends: Dict[str, IStreamBackend]) -> dict:
    """Проверка здоровья всех зарегистрированных бэкендов.

    Возвращает сводку по каждому бэкенду:
    доступность, ошибки, версия.
    """
    results = {}
    for backend_id, backend in backends.items():
        try:
            available = await backend.is_available()
            health = await backend.health_check()
            results[backend_id] = {
                "available": available,
                "details": health,
                "error": None,
            }
        except Exception as e:
            logger.warning(f"Health check для '{backend_id}' не прошел: {e}")
            results[backend_id] = {
                "available": False,
                "details": {},
                "error": str(e),
            }

    return {
        "total": len(results),
        "available": sum(1 for r in results.values() if r["available"]),
        "backends": results,
    }
