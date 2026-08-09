"""Сервисный модуль подписок на уведомления ядра и модулей (Notification Subscriptions Core)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import Request

from backend.core.database import get_db_connection
from backend.core.exceptions import NotFoundError, ValidationError
from backend.core.i18n import tr

_log = logging.getLogger("nms.subscriptions")

SEVERITY_RANKS: Dict[str, int] = {
    "info": 1,
    "success": 2,
    "warning": 3,
    "error": 4,
}

VALID_SOURCE_TYPES = {"system", "module"}
VALID_SEVERITIES = {"info", "success", "warning", "error"}
DEFAULT_CHANNELS = ["in_app"]


def _parse_subscription_row(row: Any) -> Dict[str, Any]:
    """Преобразование строки SQLite в словарь с распарсенным JSON каналов."""
    sub = dict(row)
    channels_raw = sub.get("channels_json") or '["in_app"]'
    try:
        sub["channels"] = json.loads(channels_raw) if isinstance(channels_raw, str) else channels_raw
    except Exception:
        sub["channels"] = DEFAULT_CHANNELS
    sub["enabled"] = bool(sub.get("enabled", True))
    return sub


def get_user_subscriptions(user_id: str) -> List[Dict[str, Any]]:
    """Получить список всех подписок конкретного пользователя."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, user_id, name, source_type, module_id, min_severity, channels_json, mute_until, enabled, created_at, updated_at
            FROM user_notification_subscriptions
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [_parse_subscription_row(r) for r in rows]
    finally:
        conn.close()


def get_subscription_by_id(
    sub_id: str,
    user_id: Optional[str] = None,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Получить подписку по её ID (с опциональной проверкой владельца)."""
    conn = get_db_connection()
    try:
        if user_id:
            row = conn.execute(
                """
                SELECT id, user_id, name, source_type, module_id, min_severity, channels_json, mute_until, enabled, created_at, updated_at
                FROM user_notification_subscriptions
                WHERE id = ? AND user_id = ?
                """,
                (sub_id, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT id, user_id, name, source_type, module_id, min_severity, channels_json, mute_until, enabled, created_at, updated_at
                FROM user_notification_subscriptions
                WHERE id = ?
                """,
                (sub_id,),
            ).fetchone()

        if not row:
            raise NotFoundError(
                message=tr(request, "subscription_not_found"),
                code="SUBSCRIPTION_NOT_FOUND",
                details={"sub_id": sub_id},
            )
        return _parse_subscription_row(row)
    finally:
        conn.close()


def create_subscription(
    user_id: str,
    name: str,
    source_type: str = "module",
    module_id: str = "*",
    min_severity: str = "info",
    channels: Optional[List[str]] = None,
    mute_until: Optional[str] = None,
    enabled: bool = True,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Создать подписку на события ядра или модуля."""
    source_type = source_type.lower().strip()
    if source_type not in VALID_SOURCE_TYPES:
        raise ValidationError(
            message=tr(request, "subscription_invalid_source_type", source_type=source_type),
            code="INVALID_SOURCE_TYPE",
            details={"source_type": source_type},
        )

    min_severity = min_severity.lower().strip()
    if min_severity not in VALID_SEVERITIES:
        raise ValidationError(
            message=tr(request, "subscription_invalid_severity", min_severity=min_severity),
            code="INVALID_SEVERITY",
            details={"min_severity": min_severity},
        )

    if not name or not name.strip():
        if source_type == "system":
            name = tr(request, "subscription_default_system_name")
        else:
            name = tr(request, "subscription_default_module_name", module_id=module_id)

    channels_json = json.dumps(channels if channels is not None else DEFAULT_CHANNELS)
    sub_id = f"sub_{uuid.uuid4().hex[:12]}"

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO user_notification_subscriptions (
                    id, user_id, name, source_type, module_id, min_severity, channels_json, mute_until, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sub_id, user_id, name.strip(), source_type, module_id.strip(), min_severity, channels_json, mute_until, 1 if enabled else 0),
            )
        return get_subscription_by_id(sub_id, user_id, request=request)
    finally:
        conn.close()


def update_subscription(
    sub_id: str,
    user_id: str,
    name: Optional[str] = None,
    source_type: Optional[str] = None,
    module_id: Optional[str] = None,
    min_severity: Optional[str] = None,
    channels: Optional[List[str]] = None,
    mute_until: Optional[str] = None,
    enabled: Optional[bool] = None,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Обновить существующую подписку."""
    existing = get_subscription_by_id(sub_id, user_id, request=request)

    new_source_type = (source_type or existing["source_type"]).lower().strip()
    if new_source_type not in VALID_SOURCE_TYPES:
        raise ValidationError(
            message=tr(request, "subscription_invalid_source_type", source_type=new_source_type),
            code="INVALID_SOURCE_TYPE",
            details={"source_type": new_source_type},
        )

    new_min_severity = (min_severity or existing["min_severity"]).lower().strip()
    if new_min_severity not in VALID_SEVERITIES:
        raise ValidationError(
            message=tr(request, "subscription_invalid_severity", min_severity=new_min_severity),
            code="INVALID_SEVERITY",
            details={"min_severity": new_min_severity},
        )

    new_name = name.strip() if name is not None else existing["name"]
    new_module_id = module_id.strip() if module_id is not None else existing["module_id"]
    new_channels_json = json.dumps(channels) if channels is not None else existing.get("channels_json", '["in_app"]')
    new_mute_until = mute_until if mute_until is not None else existing.get("mute_until")
    new_enabled = enabled if enabled is not None else existing["enabled"]

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE user_notification_subscriptions
                SET name = ?, source_type = ?, module_id = ?, min_severity = ?, channels_json = ?,
                    mute_until = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (new_name, new_source_type, new_module_id, new_min_severity, new_channels_json, new_mute_until, 1 if new_enabled else 0, sub_id, user_id),
            )
        return get_subscription_by_id(sub_id, user_id, request=request)
    finally:
        conn.close()


def delete_subscription(
    sub_id: str,
    user_id: str,
    request: Optional[Request] = None,
) -> bool:
    """Удалить подписку."""
    get_subscription_by_id(sub_id, user_id, request=request)
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "DELETE FROM user_notification_subscriptions WHERE id = ? AND user_id = ?",
                (sub_id, user_id),
            )
        return True
    finally:
        conn.close()


def toggle_subscription(
    sub_id: str,
    user_id: str,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Быстрое переключение активности подписки (enabled/disabled)."""
    sub = get_subscription_by_id(sub_id, user_id, request=request)
    new_state = not sub["enabled"]
    return update_subscription(sub_id, user_id, enabled=new_state, request=request)


def match_subscriptions_for_event(
    source_type: str,
    module_id: str,
    severity: str,
    conn: Any = None,
) -> Dict[str, List[str]]:
    """
    Сопоставляет входящее событие с подписками пользователей.
    Возвращает словарь {user_id: [список каналов доставки]} для всех совпавших активных подписок.
    """
    source_type = source_type.lower().strip()
    severity = severity.lower().strip()
    event_rank = SEVERITY_RANKS.get(severity, 1)

    own_conn = False
    if conn is None:
        conn = get_db_connection()
        own_conn = True

    matched: Dict[str, List[str]] = {}
    try:
        rows = conn.execute(
            """
            SELECT user_id, module_id, min_severity, channels_json, mute_until
            FROM user_notification_subscriptions
            WHERE enabled = 1
              AND (source_type = ? OR source_type = '*')
              AND (module_id = ? OR module_id = '*' OR module_id IS NULL)
            """,
            (source_type, module_id),
        ).fetchall()

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        for row in rows:
            u_id = str(row["user_id"])
            mute = row["mute_until"]
            if mute and str(mute) > now_str:
                continue

            min_sev = (row["min_severity"] or "info").lower()
            min_rank = SEVERITY_RANKS.get(min_sev, 1)

            if event_rank >= min_rank:
                try:
                    chans = json.loads(row["channels_json"]) if row["channels_json"] else ["in_app"]
                except Exception:
                    chans = ["in_app"]

                if u_id not in matched:
                    matched[u_id] = []
                for c in chans:
                    if c not in matched[u_id]:
                        matched[u_id].append(c)

        return matched
    finally:
        if own_conn:
            conn.close()


def get_subscribable_sources(request: Optional[Request] = None) -> Dict[str, Any]:
    """Возвращает структурированный словарь всех доступных источников подписок (Ядро и Модули)."""
    from backend.core.plugin.registry import get_modules

    system_source = {
        "id": "system",
        "name": tr(request, "system_core_name"),
        "description": tr(request, "system_core_desc"),
        "type": "system",
    }

    modules = []
    try:
        mod_list = get_modules()
        for m in mod_list:
            modules.append({
                "id": m.get("id"),
                "name": m.get("name") or m.get("id"),
                "description": m.get("description", ""),
                "type": "module",
                "version": m.get("version", "1.0.0"),
            })
    except Exception as exc:
        _log.warning("Could not list modules for subscriptions: %s", exc)

    return {
        "system": system_source,
        "modules": modules,
        "severities": [
            {"id": "info", "name": "INFO"},
            {"id": "success", "name": "SUCCESS"},
            {"id": "warning", "name": "WARNING"},
            {"id": "error", "name": "ERROR"},
        ],
        "available_channels": [
            {"id": "in_app", "name": tr(request, "channel_name_in_app")},
            {"id": "telegram", "name": tr(request, "channel_name_telegram")},
            {"id": "email", "name": tr(request, "channel_name_email")},
            {"id": "webhook", "name": tr(request, "channel_name_webhook")},
            {"id": "syslog", "name": tr(request, "channel_name_syslog")},
        ],
    }
