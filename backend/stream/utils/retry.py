"""Retry logic: decorator and helpers for transient failures."""
from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, TypeVar, Tuple, Type

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
