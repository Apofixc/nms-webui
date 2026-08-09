"""Inside-process EventBus for pub/sub messaging."""
from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from collections.abc import Callable
from typing import Any

from backend.core.exceptions import PermissionDeniedError

_log = logging.getLogger("nms.core.bus")


def match_topic(pattern: str, topic: str) -> bool:
    """Проверяет соответствие топика (topic) шаблону подписки (pattern).
    
    Поддерживаемые маски:
    - '*' или '#': совпадает с любым топиком.
    - '+' или '*' на позиции конкретного сегмента: совпадает с 1 любым сегментом.
    - '#' в конце маски ('segment.#'): совпадает со всеми 0+ хвостатыми сегментами.
    """
    if pattern in ("*", "#"):
        return True

    p_parts = pattern.split(".")
    t_parts = topic.split(".")

    if p_parts[-1] == "#":
        prefix_parts = p_parts[:-1]
        if len(t_parts) < len(prefix_parts):
            return False
        return all(p in ("*", "+") or p == t for p, t in zip(prefix_parts, t_parts[: len(prefix_parts)]))

    if len(p_parts) != len(t_parts):
        return False

    return all(p in ("*", "+") or p == t for p, t in zip(p_parts, t_parts))


class Subscriber:
    """Кэшированная структура данных подписчика."""

    __slots__ = ("handler", "is_async", "params_count", "pattern")

    def __init__(self, pattern: str, handler: Callable, params_count: int, is_async: bool) -> None:
        self.pattern = pattern
        self.handler = handler
        self.params_count = params_count
        self.is_async = is_async


class EventBus:
    """Внутрипроцессная шина событий pub/sub с адресацией по топикам."""

    def __init__(self) -> None:
        self._subscribers: list[Subscriber] = []
        self._lock = threading.Lock()
        self._background_tasks: set[asyncio.Task] = set()

    def subscribe(self, pattern: str, handler: Callable) -> Callable:
        """Зарегистрировать обработчик для топика или маски pattern."""
        if not callable(handler):
            raise TypeError("Handler must be callable")

        is_async = inspect.iscoroutinefunction(handler)
        params_count = len(inspect.signature(handler).parameters)
        sub = Subscriber(pattern, handler, params_count, is_async)

        with self._lock:
            if not any(s.pattern == pattern and s.handler == handler for s in self._subscribers):
                self._subscribers.append(sub)

        return handler

    def unsubscribe(self, pattern: str | Callable, handler: Callable | None = None) -> bool:
        """Отписать обработчик по (pattern, handler) или по самому handler/pattern."""
        removed = False
        with self._lock:
            if callable(pattern) and handler is None:
                target_handler = pattern
                to_remove = [s for s in self._subscribers if s.handler == target_handler]
                for s in to_remove:
                    self._subscribers.remove(s)
                    removed = True
            elif isinstance(pattern, str) and handler is not None:
                to_remove = [s for s in self._subscribers if s.pattern == pattern and s.handler == handler]
                for s in to_remove:
                    self._subscribers.remove(s)
                    removed = True
            elif isinstance(pattern, str) and handler is None:
                to_remove = [s for s in self._subscribers if s.pattern == pattern]
                for s in to_remove:
                    self._subscribers.remove(s)
                    removed = True
        return removed

    def publish(self, topic: str, payload: Any = None, is_core: bool = False) -> int:
        """Опубликовать событие в шину.

        :param topic: Топик события (например, core.modules.enabled или tuya.devices.down)
        :param payload: Данные события
        :param is_core: Флаг публикации из ядра. Публикация в core.* при is_core=False блокируется.
        :return: Количество успешно отработавших/вызванных обработчиков
        """
        if topic.startswith("core.") and not is_core:
            raise PermissionDeniedError(f"Topics starting with 'core.' are reserved for core system code: {topic}")

        with self._lock:
            matching_subs = [s for s in self._subscribers if match_topic(s.pattern, topic)]

        success_count = 0
        for sub in matching_subs:
            if self._dispatch(sub, topic, payload):
                success_count += 1

        return success_count

    def _dispatch(self, sub: Subscriber, topic: str, payload: Any) -> bool:
        """Безопасный вызов обработчика с изоляцией ошибок."""
        try:
            if sub.is_async:
                try:
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(self._safe_async_call(sub, topic, payload))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
                except RuntimeError:
                    asyncio.run(self._safe_async_call(sub, topic, payload))
            else:
                self._call_sync_handler(sub, topic, payload)
            return True
        except Exception as exc:  # noqa: BLE001
            _log.exception("Error dispatching event '%s' to subscriber %s: %s", topic, sub.handler, exc)
            return False

    async def _safe_async_call(self, sub: Subscriber, topic: str, payload: Any) -> None:
        try:
            await self._call_async_handler(sub, topic, payload)
        except Exception as exc:  # noqa: BLE001
            _log.exception("Error in async subscriber %s for topic '%s': %s", sub.handler, topic, exc)

    async def _call_async_handler(self, sub: Subscriber, topic: str, payload: Any) -> None:
        if sub.params_count == 1:
            await sub.handler(payload)
        elif sub.params_count == 0:
            await sub.handler()
        else:
            await sub.handler(topic, payload)

    def _call_sync_handler(self, sub: Subscriber, topic: str, payload: Any) -> None:
        if sub.params_count == 1:
            sub.handler(payload)
        elif sub.params_count == 0:
            sub.handler()
        else:
            sub.handler(topic, payload)


event_bus = EventBus()
