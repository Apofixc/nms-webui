"""Notify-сервис ядра для передачи уведомлений пользователям.

Обеспечивает персистентное хранение уведомлений в SQLite,
адресную доставку через WebSocket в реальном времени,
публикацию событий в EventBus и интеграцию с контекстом модулей.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from backend.core.database import get_db_connection

_log = logging.getLogger("nms.core.notify")

ALLOWED_SEVERITIES = {"info", "success", "warning", "error"}
NOTIFICATION_RETENTION_DAYS = 30


def init_notifications_db() -> None:
    """Создать таблицу notifications и индексы в базе данных, если их нет."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_id TEXT NOT NULL DEFAULT 'core',
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT DEFAULT '',
                    severity TEXT DEFAULT 'info',
                    entity_id TEXT DEFAULT NULL,
                    created_at REAL NOT NULL,
                    read_at REAL DEFAULT NULL
                );
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_user_read
                ON notifications(user_id, read_at);
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_module
                ON notifications(module_id);
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_created
                ON notifications(created_at);
            """)
    except Exception as exc:
        _log.error("Failed to initialize notifications database schema: %s", exc)
        raise
    finally:
        conn.close()


def count_unread_notifications(user_id: str) -> int:
    """Подсчитать количество непрочитанных уведомлений пользователя."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read_at IS NULL",
            (str(user_id),),
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception as exc:
        _log.error("Failed to count unread notifications for user %s: %s", user_id, exc)
        return 0
    finally:
        conn.close()


def notify(
    user_id: str,
    title: str,
    body: str = "",
    severity: str = "info",
    entity_id: Optional[str] = None,
    module_id: str = "core",
) -> Dict[str, Any]:
    """Создать базовое уведомление пользователю, сориентировать в WS и выставить событие в EventBus.

    :param user_id: ID целевого пользователя.
    :param title: Заголовок уведомления.
    :param body: Текст сообщения.
    :param severity: Уровень важности ('info', 'success', 'warning', 'error').
    :param entity_id: ID связанной сущности (опционально).
    :param module_id: Источник уведомления (модуль или 'core').
    :return: Словарь созданного уведомления.
    """
    if not user_id:
        raise ValueError("user_id is required for notify()")
    if not title:
        raise ValueError("title is required for notify()")

    sev = severity.lower() if severity else "info"
    if sev not in ALLOWED_SEVERITIES:
        sev = "info"

    created_at = time.time()
    user_str = str(user_id)

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO notifications (module_id, user_id, title, body, severity, entity_id, created_at, read_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (module_id, user_str, title, body, sev, entity_id, created_at),
            )
            notification_id = cursor.lastrowid
    finally:
        conn.close()

    notification_data: Dict[str, Any] = {
        "id": notification_id,
        "module_id": module_id,
        "user_id": user_str,
        "title": title,
        "body": body,
        "severity": sev,
        "entity_id": entity_id,
        "created_at": created_at,
        "read_at": None,
    }

    # 1. Публикация события в EventBus
    try:
        from backend.core.bus import event_bus
        event_bus.publish("core.notifications.created", notification_data, is_core=True)
    except Exception as exc:
        _log.warning("Failed to publish notification event to EventBus: %s", exc)

    # 2. Адресная WS-доставка пользователю
    try:
        from backend.core.events import ws_manager
        unread_count = count_unread_notifications(user_str)
        ws_payload = {
            "type": "notification",
            "data": notification_data,
            "unread_count": unread_count,
        }

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ws_manager.broadcast_immediate(ws_payload, target_user_id=user_str))
        except RuntimeError:
            pass
    except Exception as exc:
        _log.warning("Failed to dispatch WS notification: %s", exc)

    return notification_data


def get_user_notifications(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
) -> Dict[str, Any]:
    """Получить список уведомлений пользователя с пагинацией и количеством непрочитанных."""
    user_str = str(user_id)
    conn = get_db_connection()
    try:
        if unread_only:
            count_cur = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read_at IS NULL",
                (user_str,),
            )
            total = count_cur.fetchone()[0]

            cur = conn.execute(
                """
                SELECT id, module_id, user_id, title, body, severity, entity_id, created_at, read_at
                FROM notifications
                WHERE user_id = ? AND read_at IS NULL
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (user_str, limit, offset),
            )
        else:
            count_cur = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ?",
                (user_str,),
            )
            total = count_cur.fetchone()[0]

            cur = conn.execute(
                """
                SELECT id, module_id, user_id, title, body, severity, entity_id, created_at, read_at
                FROM notifications
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (user_str, limit, offset),
            )

        items = [dict(row) for row in cur.fetchall()]
        unread_count = count_unread_notifications(user_str)

        return {
            "items": items,
            "total": total,
            "unread_count": unread_count,
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()


def mark_as_read(notification_id: int, user_id: str) -> bool:
    """Пометить уведомление как прочитанное."""
    now = time.time()
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE notifications SET read_at = ? WHERE id = ? AND user_id = ? AND read_at IS NULL",
                (now, notification_id, str(user_id)),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def mark_all_as_read(user_id: str) -> int:
    """Пометить все непрочитанные уведомления пользователя прочитанными."""
    now = time.time()
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE notifications SET read_at = ? WHERE user_id = ? AND read_at IS NULL",
                (now, str(user_id)),
            )
            return cur.rowcount
    finally:
        conn.close()


def delete_notification(notification_id: int, user_id: str) -> bool:
    """Удалить одно конкретное уведомление пользователя."""
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM notifications WHERE id = ? AND user_id = ?",
                (notification_id, str(user_id)),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def clear_read_notifications(user_id: str) -> int:
    """Удалить все прочитанные уведомления пользователя."""
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM notifications WHERE user_id = ? AND read_at IS NOT NULL",
                (str(user_id),),
            )
            return cur.rowcount
    finally:
        conn.close()


def prune_notifications(days: int = NOTIFICATION_RETENTION_DAYS) -> int:
    """Удалить уведомления старше указанного количества дней (retention)."""
    cutoff = time.time() - (days * 86400.0)
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM notifications WHERE created_at < ?",
                (cutoff,),
            )
            count = cur.rowcount
            if count > 0:
                _log.info("Pruned %d stale notifications older than %d days", count, days)
            return count
    except Exception as exc:
        _log.error("Failed to prune notifications: %s", exc)
        return 0
    finally:
        conn.close()


def cleanup_module_notifications(module_id: str) -> int:
    """Удалить все уведомления, созданные данным модулем (при его uninstall/cleanup)."""
    if not module_id or module_id == "core":
        return 0
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM notifications WHERE module_id = ?",
                (module_id,),
            )
            count = cur.rowcount
            if count > 0:
                _log.info("Cleaned up %d notifications for uninstalled module '%s'", count, module_id)
            return count
    except Exception as exc:
        _log.error("Failed to cleanup notifications for module %s: %s", module_id, exc)
        return 0
    finally:
        conn.close()
