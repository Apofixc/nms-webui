"""Retry logic: decorator and async helpers for transient failures (e.g. stream start)."""
from __future__ import annotations

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar, Tuple, Type

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator: retry the function on given exceptions with delay and optional backoff."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc = None
            d = delay
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        time.sleep(d)
                        d *= backoff
            raise last_exc

        return wrapper  # type: ignore[return-value]

    return decorator


async def retry_async(
    coro_factory: Callable[[], Coroutine[Any, Any, Any]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Any:
    """
    Retry an async operation (e.g. stream start) with backoff.
    coro_factory: callable that returns a new coroutine each time (e.g. lambda: start_stream(...)).
    """
    last_exc = None
    d = delay
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except exceptions as e:
            last_exc = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(d)
                d *= backoff
    raise last_exc
