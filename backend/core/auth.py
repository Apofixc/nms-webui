"""Auth dependency stub — always returns anonymous user.

Replace with JWT / session-based auth when needed.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class CurrentUser:
    username: str = "anonymous"
    is_authenticated: bool = False
    permissions: tuple[str, ...] = ()


async def get_current_user(_request: Request) -> CurrentUser:
    """Dependency: returns the current user. Stub — always anonymous."""
    return CurrentUser()
