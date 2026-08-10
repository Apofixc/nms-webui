"""Notify-сервис ядра для передачи уведомлений пользователям.

Обеспечивает персистентное хранение уведомлений в SQLite,
адресную доставку через WebSocket в реальном времени,
публикацию событий в EventBus и интеграцию с контекстом модулей.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from backend.core.database import get_db_connection
from backend.core.exceptions import ValidationError

_log = logging.getLogger("nms.core.notify")

ALLOWED_SEVERITIES = {"info", "success", "warning", "error"}
ALLOWED_CATEGORIES = {"system", "security", "module", "user"}
SEVERITY_LEVELS = {"info": 1, "success": 1, "warning": 2, "error": 3}
NOTIFICATION_RETENTION_DAYS = 30

MAX_TITLE_LEN = 255
MAX_BODY_LEN = 4000


def get_notification_categories() -> List[str]:
    """Получить список всех поддерживаемых категорий уведомлений."""
    return sorted(list(ALLOWED_CATEGORIES))


def get_notification_modules() -> List[Dict[str, str]]:
    """Получить список всех зарегистрированных модулей системы для управления подписками."""
    modules = [
        {
            "id": "core",
            "name": "Ядро системы (Core)",
            "description": "Системные уведомления и важные оповещения ядра",
        }
    ]
    try:
        from backend.core.plugin.registry import get_all_manifests

        for m in get_all_manifests():
            if m.id != "core":
                modules.append({
                    "id": m.id,
                    "name": m.name or m.id,
                    "description": m.description or "",
                })
    except Exception as exc:
        _log.warning("Failed to get notification modules list: %s", exc)
    return modules


def get_notification_preferences(user_id: str, conn: Optional[Any] = None) -> Dict[str, Any]:
    """Получить предпочтения уведомлений пользователя (push, sound, subscribed_modules, module_rules)."""
    user_str = str(user_id).strip()
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True
    try:
        cur = conn.execute(
            "SELECT push_enabled, sound_enabled, subscribed_modules, module_rules FROM notification_preferences WHERE user_id = ?",
            (user_str,),
        )
        row = cur.fetchone()
        if not row:
            return {
                "user_id": user_str,
                "push_enabled": True,
                "sound_enabled": True,
                "subscribed_modules": None,
                "module_rules": {},
            }

        subscribed_modules = None
        if "subscribed_modules" in row.keys() and row["subscribed_modules"] is not None:
            try:
                sub_raw = json.loads(row["subscribed_modules"])
                if isinstance(sub_raw, list):
                    subscribed_modules = [str(m).strip() for m in sub_raw if isinstance(m, str) and m.strip()]
            except Exception:
                subscribed_modules = None

        module_rules = {}
        if "module_rules" in row.keys() and row["module_rules"]:
            try:
                rules_raw = json.loads(row["module_rules"])
                if isinstance(rules_raw, dict):
                    module_rules = rules_raw
            except Exception:
                module_rules = {}

        return {
            "user_id": user_str,
            "push_enabled": bool(row["push_enabled"]),
            "sound_enabled": bool(row["sound_enabled"]),
            "subscribed_modules": subscribed_modules,
            "module_rules": module_rules,
        }
    finally:
        if should_close:
            conn.close()


def set_notification_preferences(
    user_id: str,
    push_enabled: Optional[bool] = None,
    sound_enabled: Optional[bool] = None,
    subscribed_modules: Optional[List[str]] = None,
    module_rules: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Обновить предпочтения уведомлений пользователя."""
    user_str = str(user_id).strip()
    conn = get_db_connection()
    try:
        with conn:
            current = get_notification_preferences(user_str, conn=conn)

            new_push = push_enabled if push_enabled is not None else current["push_enabled"]
            new_sound = sound_enabled if sound_enabled is not None else current["sound_enabled"]

            if subscribed_modules is not None:
                new_subscribed = [str(m).strip() for m in subscribed_modules if isinstance(m, str) and m.strip()]
            else:
                new_subscribed = current["subscribed_modules"]

            if module_rules is not None:
                new_rules = module_rules
            else:
                new_rules = current["module_rules"]

            subscribed_json = json.dumps(new_subscribed) if new_subscribed is not None else None
            rules_json = json.dumps(new_rules)

            conn.execute(
                """
                INSERT INTO notification_preferences (user_id, push_enabled, sound_enabled, subscribed_modules, module_rules)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    push_enabled = excluded.push_enabled,
                    sound_enabled = excluded.sound_enabled,
                    subscribed_modules = excluded.subscribed_modules,
                    module_rules = excluded.module_rules
                """,
                (user_str, 1 if new_push else 0, 1 if new_sound else 0, subscribed_json, rules_json),
            )
    finally:
        conn.close()

    return {
        "user_id": user_str,
        "push_enabled": new_push,
        "sound_enabled": new_sound,
        "subscribed_modules": new_subscribed,
        "module_rules": new_rules,
    }


def count_unread_notifications(user_id: str) -> int:
    """Подсчитать количество непрочитанных уведомлений пользователя."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read_at IS NULL",
            (str(user_id).strip(),),
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
    category: str = "system",
    entity_id: Optional[str] = None,
    module_id: str = "core",
    allow_push: bool = True,
    target_url: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Создать базовое уведомление пользователю, сориентировать в WS и выставить событие в EventBus."""
    user_str = str(user_id).strip() if user_id else ""
    if not user_str:
        raise ValidationError(message="user_id is required for notify()", code="NOTIFY_MISSING_USER_ID")

    title_str = str(title).strip() if title else ""
    if not title_str:
        raise ValidationError(message="title is required for notify()", code="NOTIFY_MISSING_TITLE")

    # Обрезка слишком длинных заголовков и текста
    if len(title_str) > MAX_TITLE_LEN:
        title_str = title_str[: MAX_TITLE_LEN - 3] + "..."

    body_str = str(body) if body else ""
    if len(body_str) > MAX_BODY_LEN:
        body_str = body_str[: MAX_BODY_LEN - 3] + "..."

    sev = severity.lower().strip() if severity else "info"
    if sev not in ALLOWED_SEVERITIES:
        sev = "info"

    cat = category.lower().strip() if category else "system"
    if cat not in ALLOWED_CATEGORIES:
        cat = "system"

    mod_id = module_id.strip() if module_id else "core"

    prefs = get_notification_preferences(user_str)

    # 1. Проверка явной подписки на модуль (core всегда разрешен)
    sub_modules = prefs.get("subscribed_modules")
    if sub_modules is not None and isinstance(sub_modules, list):
        if mod_id != "core" and mod_id not in sub_modules:
            _log.info("Notification omitted for user %s because module '%s' is not in subscribed_modules", user_str, mod_id)
            return None

    # 2. Проверка порога важности (min_severity) и активности модуля
    rules = prefs.get("module_rules", {})
    if isinstance(rules, dict) and mod_id in rules:
        mod_rule = rules[mod_id]
        if isinstance(mod_rule, dict):
            if mod_rule.get("enabled") is False or mod_rule.get("disabled") is True:
                _log.info("Notification omitted for user %s: module '%s' is disabled in module_rules", user_str, mod_id)
                return None
            min_sev = mod_rule.get("min_severity")
            if min_sev and min_sev in SEVERITY_LEVELS:
                if SEVERITY_LEVELS.get(sev, 1) < SEVERITY_LEVELS[min_sev]:
                    _log.info(
                        "Notification omitted for user %s: severity '%s' for module '%s' is below threshold '%s'",
                        user_str, sev, mod_id, min_sev
                    )
                    return None

    created_at = time.time()

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO notifications (module_id, user_id, title, body, severity, category, entity_id, target_url, created_at, read_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (mod_id, user_str, title_str, body_str, sev, cat, entity_id, target_url, created_at),
            )
            notification_id = cursor.lastrowid
    finally:
        conn.close()

    notification_data: Dict[str, Any] = {
        "id": notification_id,
        "module_id": mod_id,
        "user_id": user_str,
        "title": title_str,
        "body": body_str,
        "severity": sev,
        "category": cat,
        "entity_id": entity_id,
        "target_url": target_url,
        "created_at": created_at,
        "read_at": None,
    }

    # 1. Публикация события в EventBus
    try:
        from backend.core.bus import event_bus
        event_bus.publish("core.notifications.created", notification_data, is_core=True)
    except Exception as exc:
        _log.warning("Failed to publish notification event to EventBus: %s", exc)

    # 2. Адресная WS-доставка пользователю (с гарантией работы из фоновых потоков)
    try:
        from backend.core.events import ws_manager
        unread_count = count_unread_notifications(user_str)
        ws_payload = {
            "type": "notification",
            "data": notification_data,
            "unread_count": unread_count,
            "push_eligible": allow_push and prefs["push_enabled"],
            "sound_eligible": prefs["sound_enabled"],
        }

        coro = ws_manager.broadcast_immediate(ws_payload, target_user_id=user_str)
        scheduled = False
        try:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
                if getattr(ws_manager, "_loop", None) is None:
                    ws_manager._loop = loop
                scheduled = True
            except RuntimeError:
                try:
                    loop = ws_manager._loop
                    if loop is None:
                        loop = asyncio.get_event_loop()
                    if loop and loop.is_running():
                        asyncio.run_coroutine_threadsafe(coro, loop)
                        scheduled = True
                except Exception as exc:
                    _log.warning("Failed to dispatch WS notification from thread context: %s", exc)
        finally:
            if not scheduled:
                coro.close()
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
    user_str = str(user_id).strip()
    conn = get_db_connection()
    try:
        # Всегда считаем общее количество уведомлений пользователя
        total_cur = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ?",
            (user_str,),
        )
        total = total_cur.fetchone()[0]

        # Всегда считаем количество непрочитанных
        unread_cur = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read_at IS NULL",
            (user_str,),
        )
        unread_count = unread_cur.fetchone()[0]

        filtered_total = unread_count if unread_only else total

        if unread_only:
            cur = conn.execute(
                """
                SELECT id, module_id, user_id, title, body, severity, category, entity_id, target_url, created_at, read_at
                FROM notifications
                WHERE user_id = ? AND read_at IS NULL
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (user_str, limit, offset),
            )
        else:
            cur = conn.execute(
                """
                SELECT id, module_id, user_id, title, body, severity, category, entity_id, target_url, created_at, read_at
                FROM notifications
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (user_str, limit, offset),
            )

        items = [dict(row) for row in cur.fetchall()]

        return {
            "items": items,
            "total": total,
            "filtered_total": filtered_total,
            "unread_count": unread_count,
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()


def mark_as_read(notification_id: int, user_id: str) -> bool:
    """Пометить уведомление как прочитанное (идемпотентно для принадлежащих пользователю)."""
    now = time.time()
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE notifications SET read_at = COALESCE(read_at, ?) WHERE id = ? AND user_id = ?",
                (now, notification_id, str(user_id).strip()),
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
                (now, str(user_id).strip()),
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
                (notification_id, str(user_id).strip()),
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
                (str(user_id).strip(),),
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
