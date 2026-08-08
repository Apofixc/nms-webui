"""Rate limiting module (in-memory sliding window).

Обеспечивает ограничение частоты запросов для чувствительных эндпоинтов (auth, MFA).
"""
from __future__ import annotations

import time
import logging
from typing import Dict, List, Optional
from fastapi import Request

from backend.core.exceptions import RateLimitExceededError
from backend.core.i18n import tr

_log = logging.getLogger("nms.rate_limiter")


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self):
        self._history: Dict[str, List[float]] = {}

    def is_allowed(self, key: str, max_requests: int = 5, window_seconds: int = 60) -> bool:
        """Проверить, не превышен ли лимит вызовов для ключа."""
        now = time.time()
        cutoff = now - window_seconds

        history = self._history.get(key, [])
        # Очистка устаревших отметок
        history = [t for t in history if t > cutoff]
        self._history[key] = history

        if len(history) >= max_requests:
            return False

        history.append(now)
        return True

    def reset(self, key: str) -> None:
        """Сбросить счетчик для ключа."""
        self._history.pop(key, None)

    def clear(self) -> None:
        """Сбросить все счетчики (для тестов)."""
        self._history.clear()


rate_limiter = SlidingWindowRateLimiter()


def enforce_rate_limit(
    request: Request,
    action: str,
    username: Optional[str] = None,
    max_requests: int = 5,
    window_seconds: int = 60,
) -> None:
    """Проверить rate limit и выкинуть RateLimitExceededError при превышении."""
    from backend.core.plugin.registry import get_security_settings
    sec_settings = get_security_settings()

    # Считывание настроек из безопасности, если заданы
    cfg_max = int(sec_settings.get(f"rate_limit_{action}_max", max_requests))
    cfg_win = int(sec_settings.get(f"rate_limit_{action}_window", window_seconds))

    client_ip = request.client.host if request and request.client else "unknown"
    key = f"{action}:{client_ip}:{username or ''}"

    if not rate_limiter.is_allowed(key, max_requests=cfg_max, window_seconds=cfg_win):
        _log.warning("Rate limit exceeded for key %s (max %d in %ds)", key, cfg_max, cfg_win)
        raise RateLimitExceededError(
            message=tr(request, "rate_limit_exceeded"),
            code="RATE_LIMIT_EXCEEDED",
            details={"action": action, "retry_after": cfg_win},
        )
