"""Audit logging system.

Provides functions to record system actions, authentication events, and security logs.
"""
from __future__ import annotations

import logging
from typing import Optional
from backend.core.database import get_db_connection

_log = logging.getLogger("nms.audit")


def log_audit_event(
    user_id: Optional[str],
    username: str,
    action: str,
    resource: str,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Записать событие аудита в базу данных."""
    try:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO audit_logs (user_id, username, action, resource, details, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, username, action, resource, details, ip_address),
                )
        finally:
            conn.close()
    except Exception as exc:
        _log.error("Failed to write audit log: %s", exc)
