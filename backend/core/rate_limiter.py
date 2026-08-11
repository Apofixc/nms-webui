"""In-memory sliding window rate limiter per IP + username."""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        """Проверить превышение лимита запросов.

        :param key: уникальный ключ (например ip + ":" + username + ":" + route)
        :param max_requests: максимальное число допустимых запросов за окно
        :param window_seconds: длительность окна в секундах
        :return: True если лимит превышен (блокировать), False если запрос разрешён
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._requests[key]
            # Очистка устаревших отметок
            self._requests[key] = [t for t in timestamps if t > cutoff]
            timestamps = self._requests[key]

            if len(timestamps) >= max_requests:
                return True

            timestamps.append(now)
            return False

    def clear(self):
        """Очистить сохранённое состояние."""
        with self._lock:
            self._requests.clear()


rate_limiter = RateLimiter()
