"""Inside-process EventBus for pub/sub messaging."""
from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable

from backend.core.exceptions import PermissionDeniedError

_log = logging.getLogger("nms.core.bus")


def match_topic(pattern: str, topic: str) -> bool:
    """Проверяет соответствие топика (topic) шаблону подписки (pattern).
    
    Поддерживаемые маски:
    - '*' или '#': совпадает с любым топиком.
    - '*' на позиции конкретного сегмента: совпадает с любым значением этого сегмента.
    - Законченная маска 'segment.*': совпадает со всеми подтопиками с префиксом 'segment.'.
    """
    if pattern in ("*", "#"):
        return True

    p_parts = pattern.split(".")
    t_parts = topic.split(".")

    # Случай префиксной маски, например "core.*" или "tuya.devices.*"
    if p_parts[-1] == "*":
        prefix_parts = p_parts[:-1]
        if len(t_parts) >= len(prefix_parts):
            if all(p == "*" or p == t for p, t in zip(prefix_parts, t_parts[:len(prefix_parts)])):
                return True

    if len(p_parts) != len(t_parts):
        return False

    return all(p == "*" or p == t for p, t in zip(p_parts, t_parts))


class EventBus:
    """Внутрипроцессная шина событий pub/sub с адресацией по топикам."""

    def __init__(self) -> None:
        self._subscribers: list[tuple[str, Callable]] = []

    def subscribe(self, pattern: str, handler: Callable) -> Callable:
        """Зарегистрировать обработчик для топика или маски pattern."""
        if not callable(handler):
            raise ValueError("Handler must be callable")
        sub = (pattern, handler)
        if sub not in self._subscribers:
            self._subscribers.append(sub)
        return handler

    def unsubscribe(self, pattern: str | Callable, handler: Callable | None = None) -> bool:
        """Отписать обработчик по (pattern, handler) или по самому handler/pattern."""
        removed = False
        if callable(pattern) and handler is None:
            target_handler = pattern
            to_remove = [s for s in self._subscribers if s[1] == target_handler]
            for s in to_remove:
                self._subscribers.remove(s)
                removed = True
        elif isinstance(pattern, str) and handler is not None:
            sub = (pattern, handler)
            if sub in self._subscribers:
                self._subscribers.remove(sub)
                removed = True
        elif isinstance(pattern, str) and handler is None:
            to_remove = [s for s in self._subscribers if s[0] == pattern]
            for s in to_remove:
                self._subscribers.remove(s)
                removed = True
        return removed

    def publish(self, topic: str, payload: Any = None, is_core: bool = True) -> int:
        """Опубликовать событие в шину.

        :param topic: Топик события (например, core.modules.enabled или tuya.devices.down)
        :param payload: Данные события
        :param is_core: Флаг публикации из ядра. Публикация в core.* при is_core=False блокируется.
        :return: Количество вызванных обработчиков
        """
        if topic.startswith("core.") and not is_core:
            raise PermissionDeniedError(f"Topics starting with 'core.' are reserved for core system code: {topic}")

        matching_handlers = [handler for pattern, handler in list(self._subscribers) if match_topic(pattern, topic)]

        for handler in matching_handlers:
            self._dispatch(handler, topic, payload)

        return len(matching_handlers)

    def _dispatch(self, handler: Callable, topic: str, payload: Any) -> None:
        """Безопасный вызов обработчика с изоляцией ошибок."""
        try:
            if inspect.iscoroutinefunction(handler):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._safe_async_call(handler, topic, payload))
                except RuntimeError:
                    asyncio.run(self._safe_async_call(handler, topic, payload))
            else:
                self._call_sync_handler(handler, topic, payload)
        except Exception as exc:
            _log.exception("Error dispatching event '%s' to subscriber %s: %s", topic, handler, exc)

    async def _safe_async_call(self, handler: Callable, topic: str, payload: Any) -> None:
        try:
            await self._call_async_handler(handler, topic, payload)
        except Exception as exc:
            _log.exception("Error in async subscriber %s for topic '%s': %s", handler, topic, exc)

    async def _call_async_handler(self, handler: Callable, topic: str, payload: Any) -> None:
        sig = inspect.signature(handler)
        params_count = len(sig.parameters)
        if params_count == 1:
            await handler(payload)
        elif params_count == 0:
            await handler()
        else:
            await handler(topic, payload)

    def _call_sync_handler(self, handler: Callable, topic: str, payload: Any) -> None:
        sig = inspect.signature(handler)
        params_count = len(sig.parameters)
        if params_count == 1:
            handler(payload)
        elif params_count == 0:
            handler()
        else:
            handler(topic, payload)


event_bus = EventBus()
