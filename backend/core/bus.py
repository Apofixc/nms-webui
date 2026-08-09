"""Inside-process EventBus for pub/sub messaging."""
from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from collections.abc import Callable
from typing import Any

from backend.core.exceptions import PermissionDeniedError, ValidationError

_log = logging.getLogger("nms.core.bus")


def match_topic(pattern: str, topic: str) -> bool:
    """Проверяет соответствие топика (topic) шаблону подписки (pattern).
    
    Поддерживаемые маски:
    - '*' или '#': совпадает с любым топиком.
    - '+' или '*' на позиции конкретного сегмента: совпадает с 1 любым сегментом.
    - '#' в конце маски ('segment.#'): совпадает со всеми 0+ хвостатыми сегментами.
    """
    if pattern in ("*", "#") or pattern == topic:
        return True

    # Быстрый отказ: если в маске нет спецсимволов wildcard, то топик должен совпадать точно
    if "*" not in pattern and "+" not in pattern and "#" not in pattern:
        return False

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


def _inspect_subscriber_params(handler: Callable) -> int:
    """Определяет количество передаваемых аргументов для обработчика (0, 1 или 2)."""
    try:
        sig = inspect.signature(handler)
        # Если параметр с переменным числом позиционных аргументов (*args)
        if any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values()):
            return 2

        pos_params = [
            p for p in sig.parameters.values()
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        req_pos_params = [p for p in pos_params if p.default == inspect.Parameter.empty]
        # Если ровно 1 обязательный параметр из нескольких позиционных — передавать только payload
        if len(req_pos_params) == 1 and len(pos_params) > 1:
            return 1
        return len(pos_params)
    except (ValueError, TypeError):
        return 1


class Subscriber:
    """Кэшированная структура данных подписчика."""

    __slots__ = ("handler", "has_wildcard", "is_async", "params_count", "pattern")

    def __init__(self, pattern: str, handler: Callable, params_count: int, is_async: bool) -> None:
        self.pattern = pattern
        self.handler = handler
        self.params_count = params_count
        self.is_async = is_async
        self.has_wildcard = any(char in pattern for char in ("*", "+", "#"))


class EventBus:
    """Внутрипроцессная шина событий pub/sub с адресацией по топикам."""

    def __init__(self) -> None:
        self._subscribers: list[Subscriber] = []
        self._exact_subscribers: dict[str, list[Subscriber]] = {}
        self._wildcard_subscribers: list[Subscriber] = []
        self._lock = threading.Lock()
        self._background_tasks: set[asyncio.Task] = set()

    def subscribe(self, pattern: str, handler: Callable) -> Callable:
        """Зарегистрировать обработчик для топика или маски pattern."""
        if not callable(handler):
            raise ValidationError(message="Handler must be callable", code="INVALID_HANDLER")

        is_async = inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(handler)
        params_count = _inspect_subscriber_params(handler)
        sub = Subscriber(pattern, handler, params_count, is_async)

        with self._lock:
            if not any(s.pattern == pattern and s.handler == handler for s in self._subscribers):
                self._subscribers.append(sub)
                if sub.has_wildcard:
                    self._wildcard_subscribers.append(sub)
                else:
                    self._exact_subscribers.setdefault(pattern, []).append(sub)

        return handler

    def unsubscribe(self, pattern: str | Callable, handler: Callable | None = None) -> bool:
        """Отписать обработчик по (pattern, handler) или по самому handler/pattern."""
        with self._lock:
            initial_len = len(self._subscribers)
            if callable(pattern) and handler is None:
                self._subscribers = [s for s in self._subscribers if s.handler != pattern]
            elif isinstance(pattern, str) and handler is not None:
                self._subscribers = [s for s in self._subscribers if not (s.pattern == pattern and s.handler == handler)]
            elif isinstance(pattern, str) and handler is None:
                self._subscribers = [s for s in self._subscribers if s.pattern != pattern]
            
            removed = len(self._subscribers) < initial_len
            if removed:
                self._reindex_subscribers()
            return removed

    def _reindex_subscribers(self) -> None:
        """Переиндексация точечных подписок и подписок по маске (вызывать под _lock)."""
        self._exact_subscribers.clear()
        self._wildcard_subscribers.clear()
        for sub in self._subscribers:
            if sub.has_wildcard:
                self._wildcard_subscribers.append(sub)
            else:
                self._exact_subscribers.setdefault(sub.pattern, []).append(sub)

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
            matching_subs = list(self._exact_subscribers.get(topic, []))
            if self._wildcard_subscribers:
                matching_subs.extend(s for s in self._wildcard_subscribers if match_topic(s.pattern, topic))

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
                    with self._lock:
                        self._background_tasks.add(task)

                    def _on_task_done(t: asyncio.Task) -> None:
                        with self._lock:
                            self._background_tasks.discard(t)

                    task.add_done_callback(_on_task_done)
                except RuntimeError:
                    # ponytail: синхронный фоновый поток без запущенного event loop
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

    def clear(self) -> None:
        """Очистить всех зарегистрированных подписчиков."""
        with self._lock:
            self._subscribers.clear()
            self._exact_subscribers.clear()
            self._wildcard_subscribers.clear()

    def get_stats(self) -> dict[str, Any]:
        """Возвращает текущую статистику шины событий."""
        with self._lock:
            subscribers_count = len(self._subscribers)
            patterns = list({s.pattern for s in self._subscribers})
            active_tasks = len(self._background_tasks)
        return {
            "subscribers_count": subscribers_count,
            "patterns_count": len(patterns),
            "patterns": patterns,
            "active_tasks_count": active_tasks,
        }

    async def shutdown(self, timeout: float = 5.0) -> None:
        """Остановить шину событий: отписать всех подписчиков и завершить фоновые задачи."""
        with self._lock:
            tasks = list(self._background_tasks)
            self._subscribers.clear()
            self._exact_subscribers.clear()
            self._wildcard_subscribers.clear()

        if not tasks:
            return

        _done, pending = await asyncio.wait(tasks, timeout=timeout)
        for task in pending:
            task.cancel()

        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


event_bus = EventBus()



