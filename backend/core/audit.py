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


def rotate_audit_logs(max_days: int = 90, max_records: int = 100000) -> int:
    """Удаление устаревших записей аудита по дням и ограничению количества.
    Возвращает количество удаленных записей.
    """
    deleted_count = 0
    try:
        conn = get_db_connection()
        try:
            with conn:
                # 1. Удаление записей старше max_days
                cur = conn.execute(
                    """
                    DELETE FROM audit_logs
                    WHERE (julianday('now') - julianday(replace(created_at, 'T', ' '))) > ?
                    """,
                    (max_days,),
                )
                deleted_count += cur.rowcount

                # 2. Ограничение общего количества записей до max_records (удаление самых старых)
                cur = conn.execute(
                    """
                    DELETE FROM audit_logs
                    WHERE id NOT IN (
                        SELECT id FROM audit_logs ORDER BY id DESC LIMIT ?
                    )
                    """,
                    (max_records,),
                )
                deleted_count += cur.rowcount
        finally:
            conn.close()
    except Exception as exc:
        _log.error("Failed to rotate audit logs: %s", exc)
    return deleted_count
