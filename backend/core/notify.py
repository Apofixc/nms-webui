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

_UNREAD_COUNT_CACHE: Dict[str, int] = {}


def invalidate_unread_cache(user_id: Optional[str] = None) -> None:
    """Очистить/инвалидировать кэш непрочитанных уведомлений."""
    if user_id:
        _UNREAD_COUNT_CACHE.pop(str(user_id).strip(), None)
    else:
        _UNREAD_COUNT_CACHE.clear()


def is_quiet_hours(quiet_hours: Dict[str, Any]) -> bool:
    """Проверить, действуют ли сейчас тихие часы пользователя с учетом цикличности."""
    if not isinstance(quiet_hours, dict) or not quiet_hours.get("enabled"):
        return False
    start_str = quiet_hours.get("start")
    end_str = quiet_hours.get("end")
    if not start_str or not end_str:
        return False

    days_mode = quiet_hours.get("days", "everyday")
    now_lt = time.localtime()
    wday = now_lt.tm_wday  # 0=Mon, 4=Fri, 5=Sat, 6=Sun

    if days_mode == "weekdays" and wday >= 5:
        return False
    elif days_mode == "weekends" and wday < 5:
        return False
    elif isinstance(days_mode, list) and len(days_mode) > 0:
        if wday not in days_mode:
            return False

    try:
        now_minutes = now_lt.tm_hour * 60 + now_lt.tm_min

        sh, sm = map(int, str(start_str).split(":"))
        eh, em = map(int, str(end_str).split(":"))
        start_min = sh * 60 + sm
        end_min = eh * 60 + em

        if start_min < end_min:
            return start_min <= now_minutes < end_min
        else:
            return now_minutes >= start_min or now_minutes < end_min
    except Exception:
        return False


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


_UNSET = object()


def get_notification_preferences(user_id: str, conn: Optional[Any] = None) -> Dict[str, Any]:
    """Получить предпочтения уведомлений пользователя (push, sound, subscribed_modules, module_rules, sound_signals, muted_until)."""
    user_str = str(user_id).strip()
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True
    try:
        table_info = conn.execute("PRAGMA table_info(notification_preferences)").fetchall()
        pref_cols = {col["name"] for col in table_info}
        muted_sql = ", muted_until" if "muted_until" in pref_cols else ""
        quiet_sql = ", quiet_hours" if "quiet_hours" in pref_cols else ""
        cur = conn.execute(
            f"SELECT push_enabled, sound_enabled, subscribed_modules, module_rules, sound_signals{muted_sql}{quiet_sql} FROM notification_preferences WHERE user_id = ?",
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
                "sound_signals": {},
                "muted_until": None,
                "quiet_hours": {},
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
                    now_ts = time.time()
                    for m_id, r_val in rules_raw.items():
                        if isinstance(r_val, dict):
                            r_copy = dict(r_val)
                            if r_copy.get("muted_until") is not None:
                                try:
                                    m_until = float(r_copy["muted_until"])
                                    if m_until == -1:
                                        r_copy["muted_until"] = -1.0
                                    elif m_until <= now_ts:
                                        r_copy["muted_until"] = None
                                    else:
                                        r_copy["muted_until"] = m_until
                                except (ValueError, TypeError):
                                    r_copy["muted_until"] = None
                            module_rules[m_id] = r_copy
            except Exception:
                module_rules = {}

        sound_signals = {}
        if "sound_signals" in row.keys() and row["sound_signals"]:
            try:
                signals_raw = json.loads(row["sound_signals"])
                if isinstance(signals_raw, dict):
                    sound_signals = signals_raw
            except Exception:
                sound_signals = {}

        muted_until = None
        if "muted_until" in row.keys() and row["muted_until"] is not None:
            try:
                val = float(row["muted_until"])
                if val == -1:
                    muted_until = -1.0
                elif val > time.time():
                    muted_until = val
            except (ValueError, TypeError):
                muted_until = None

        quiet_hours = {}
        if "quiet_hours" in row.keys() and row["quiet_hours"]:
            try:
                qh_raw = json.loads(row["quiet_hours"])
                if isinstance(qh_raw, dict):
                    quiet_hours = qh_raw
            except Exception:
                quiet_hours = {}

        return {
            "user_id": user_str,
            "push_enabled": bool(row["push_enabled"]),
            "sound_enabled": bool(row["sound_enabled"]),
            "subscribed_modules": subscribed_modules,
            "module_rules": module_rules,
            "sound_signals": sound_signals,
            "muted_until": muted_until,
            "quiet_hours": quiet_hours,
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
    sound_signals: Optional[Dict[str, str]] = None,
    muted_until: Any = _UNSET,
    quiet_hours: Optional[Dict[str, Any]] = None,
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

            if sound_signals is not None:
                new_signals = sound_signals
            else:
                new_signals = current["sound_signals"]

            if muted_until is not _UNSET:
                if muted_until is None or (isinstance(muted_until, (int, float)) and float(muted_until) == 0):
                    new_muted_until = None
                elif isinstance(muted_until, (int, float)) and float(muted_until) < 0:
                    new_muted_until = -1.0
                else:
                    new_muted_until = float(muted_until)
            else:
                new_muted_until = current["muted_until"]

            if quiet_hours is not None:
                new_quiet = quiet_hours
            else:
                new_quiet = current.get("quiet_hours", {})

            subscribed_json = json.dumps(new_subscribed) if new_subscribed is not None else None
            rules_json = json.dumps(new_rules)
            signals_json = json.dumps(new_signals)
            quiet_json = json.dumps(new_quiet)

            table_info = conn.execute("PRAGMA table_info(notification_preferences)").fetchall()
            has_qh_col = any(col["name"] == "quiet_hours" for col in table_info)

            if has_qh_col:
                conn.execute(
                    """
                    INSERT INTO notification_preferences (user_id, push_enabled, sound_enabled, subscribed_modules, module_rules, sound_signals, muted_until, quiet_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        push_enabled = excluded.push_enabled,
                        sound_enabled = excluded.sound_enabled,
                        subscribed_modules = excluded.subscribed_modules,
                        module_rules = excluded.module_rules,
                        sound_signals = excluded.sound_signals,
                        muted_until = excluded.muted_until,
                        quiet_hours = excluded.quiet_hours
                    """,
                    (user_str, 1 if new_push else 0, 1 if new_sound else 0, subscribed_json, rules_json, signals_json, new_muted_until, quiet_json),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO notification_preferences (user_id, push_enabled, sound_enabled, subscribed_modules, module_rules, sound_signals, muted_until)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        push_enabled = excluded.push_enabled,
                        sound_enabled = excluded.sound_enabled,
                        subscribed_modules = excluded.subscribed_modules,
                        module_rules = excluded.module_rules,
                        sound_signals = excluded.sound_signals,
                        muted_until = excluded.muted_until
                    """,
                    (user_str, 1 if new_push else 0, 1 if new_sound else 0, subscribed_json, rules_json, signals_json, new_muted_until),
                )
    finally:
        conn.close()

    return {
        "user_id": user_str,
        "push_enabled": new_push,
        "sound_enabled": new_sound,
        "subscribed_modules": new_subscribed,
        "module_rules": new_rules,
        "sound_signals": new_signals,
        "muted_until": new_muted_until,
        "quiet_hours": new_quiet,
    }


def count_unread_notifications(user_id: str, conn: Optional[Any] = None) -> int:
    """Подсчитать количество непрочитанных уведомлений пользователя (с in-memory кэшированием)."""
    user_key = str(user_id).strip()
    if conn is None and user_key in _UNREAD_COUNT_CACHE:
        return _UNREAD_COUNT_CACHE[user_key]

    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True
    try:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read_at IS NULL",
            (user_key,),
        )
        row = cursor.fetchone()
        cnt = row[0] if row else 0
        _UNREAD_COUNT_CACHE[user_key] = cnt
        return cnt
    except Exception as exc:
        _log.error("Failed to count unread notifications for user %s: %s", user_id, exc)
        return 0
    finally:
        if should_close:
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
    actions: Optional[List[Dict[str, Any]]] = None,
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

    conn = get_db_connection()
    try:
        prefs = get_notification_preferences(user_str, conn=conn)

        # 0. Проверка глобального временного отключения (muted_until)
        g_muted_until = prefs.get("muted_until")
        if g_muted_until is not None:
            try:
                f_g_mute = float(g_muted_until)
                if f_g_mute == -1 or time.time() < f_g_mute:
                    _log.info("Notification omitted for user %s: notifications are temporarily muted until %s", user_str, g_muted_until)
                    return None
            except (ValueError, TypeError):
                pass

        # 1. Проверка явных правил модуля в module_rules (имеет высший приоритет)
        rules = prefs.get("module_rules", {})
        if isinstance(rules, dict) and mod_id in rules:
            mod_rule = rules[mod_id]
            if isinstance(mod_rule, dict):
                if mod_rule.get("enabled") is False or mod_rule.get("disabled") is True:
                    _log.info("Notification omitted for user %s: module '%s' is disabled in module_rules", user_str, mod_id)
                    return None
                m_muted_until = mod_rule.get("muted_until")
                if m_muted_until is not None:
                    try:
                        f_m_mute = float(m_muted_until)
                        if f_m_mute == -1 or time.time() < f_m_mute:
                            _log.info("Notification omitted for user %s: module '%s' is temporarily muted until %s", user_str, mod_id, m_muted_until)
                            return None
                    except (ValueError, TypeError):
                        pass

                min_sev = mod_rule.get("min_severity")
                if min_sev and min_sev in SEVERITY_LEVELS:
                    if SEVERITY_LEVELS.get(sev, 1) < SEVERITY_LEVELS[min_sev]:
                        _log.info(
                            "Notification omitted for user %s: severity '%s' for module '%s' is below threshold '%s'",
                            user_str, sev, mod_id, min_sev
                        )
                        return None

        # 2. Проверка белого списка подписок subscribed_modules
        sub_modules = prefs.get("subscribed_modules")
        if sub_modules is not None and isinstance(sub_modules, list):
            if mod_id != "core" and mod_id not in sub_modules:
                # Если в module_rules модуль не был явно разрешен (enabled = True)
                if not (isinstance(rules, dict) and rules.get(mod_id, {}).get("enabled") is True):
                    _log.info(
                        "Notification omitted for user %s: module '%s' is not in subscribed_modules and not explicitly enabled",
                        user_str, mod_id
                    )
                    return None


        created_at = time.time()

        notification_id = 0
        unread_count = 0
        group_count = 1

        # Проверка наличия колонок group_count и actions в текущей БД
        table_info = conn.execute("PRAGMA table_info(notifications)").fetchall()
        has_group_col = any(col["name"] == "group_count" for col in table_info)
        has_actions_col = any(col["name"] == "actions" for col in table_info)

        actions_json = json.dumps(actions) if actions and isinstance(actions, list) else None

        # Повторные попытки при блокировках SQLite (database is locked)
        for attempt in range(5):
            try:
                with conn:
                    if has_group_col:
                        # Проверка дедупликации: ищем недавнее непрочитанное уведомление с совпадающими параметрами за 60 секунд
                        cutoff = created_at - 60.0
                        dup_cur = conn.execute(
                            """
                            SELECT id, group_count FROM notifications
                            WHERE user_id = ? AND module_id = ? AND category = ? AND severity = ? AND title = ? AND read_at IS NULL AND created_at >= ?
                            ORDER BY id DESC LIMIT 1
                            """,
                            (user_str, mod_id, cat, sev, title_str, cutoff),
                        )
                        dup_row = dup_cur.fetchone()
                        if dup_row:
                            notification_id = dup_row["id"]
                            group_count = (dup_row["group_count"] or 1) + 1
                            if has_actions_col:
                                conn.execute(
                                    """
                                    UPDATE notifications
                                    SET group_count = ?, created_at = ?, body = CASE WHEN ? != '' THEN ? ELSE body END, actions = COALESCE(?, actions)
                                    WHERE id = ?
                                    """,
                                    (group_count, created_at, body_str, body_str, actions_json, notification_id),
                                )
                            else:
                                conn.execute(
                                    """
                                    UPDATE notifications
                                    SET group_count = ?, created_at = ?, body = CASE WHEN ? != '' THEN ? ELSE body END
                                    WHERE id = ?
                                    """,
                                    (group_count, created_at, body_str, body_str, notification_id),
                                )
                        else:
                            if has_actions_col:
                                cursor = conn.execute(
                                    """
                                    INSERT INTO notifications (module_id, user_id, title, body, severity, category, entity_id, target_url, group_count, actions, created_at, read_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, NULL)
                                    """,
                                    (mod_id, user_str, title_str, body_str, sev, cat, entity_id, target_url, actions_json, created_at),
                                )
                            else:
                                cursor = conn.execute(
                                    """
                                    INSERT INTO notifications (module_id, user_id, title, body, severity, category, entity_id, target_url, group_count, created_at, read_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, NULL)
                                    """,
                                    (mod_id, user_str, title_str, body_str, sev, cat, entity_id, target_url, created_at),
                                )
                            notification_id = cursor.lastrowid
                            group_count = 1
                    else:
                        cursor = conn.execute(
                            """
                            INSERT INTO notifications (module_id, user_id, title, body, severity, category, entity_id, target_url, created_at, read_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                            """,
                            (mod_id, user_str, title_str, body_str, sev, cat, entity_id, target_url, created_at),
                        )
                        notification_id = cursor.lastrowid
                        group_count = 1

                    invalidate_unread_cache(user_str)
                    unread_count = count_unread_notifications(user_str, conn=conn)
                break
            except Exception as exc:
                if "locked" in str(exc).lower() and attempt < 4:
                    time.sleep(0.05 * (2 ** attempt))
                    continue
                _log.error("Failed to insert/update notification into DB: %s", exc)
                raise
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
        "group_count": group_count,
        "actions": actions if actions and isinstance(actions, list) else None,
        "acknowledged_at": None,
        "acknowledged_by": None,
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

        # Определение звукового сигнала для данного уведомления
        mod_rule_sound = rules.get(mod_id, {}).get("sound_signal") if isinstance(rules, dict) else None
        sev_sound = prefs.get("sound_signals", {}).get(sev) if isinstance(prefs.get("sound_signals"), dict) else None
        target_sound = mod_rule_sound or sev_sound or "default"

        is_qh = is_quiet_hours(prefs.get("quiet_hours", {}))
        push_elig = allow_push and prefs["push_enabled"] and (not is_qh or sev == "error")
        sound_elig = prefs["sound_enabled"] and (not is_qh or sev == "error")

        ws_payload = {
            "type": "notification",
            "data": notification_data,
            "unread_count": unread_count,
            "push_eligible": push_elig,
            "sound_eligible": sound_elig,
            "sound_signal": target_sound,
        }

        coro = ws_manager.broadcast_immediate(ws_payload, target_user_id=user_str)
        scheduled = False
        try:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
                ws_manager.update_loop_if_needed(loop)
                scheduled = True
            except RuntimeError:
                target_loop = getattr(ws_manager, "_loop", None)
                if target_loop and not target_loop.is_closed() and target_loop.is_running():
                    asyncio.run_coroutine_threadsafe(coro, target_loop)
                    scheduled = True
                else:
                    _log.warning("Failed to dispatch WS notification from thread context: no running event loop available")
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
    severity: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Получить список уведомлений пользователя с фильтрацией, пагинацией и количеством непрочитанных."""
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

        # Динамическое формирование WHERE для списка с фильтрацией
        where_clauses = ["user_id = ?"]
        params: List[Any] = [user_str]

        if unread_only:
            where_clauses.append("read_at IS NULL")

        if severity and severity.strip():
            where_clauses.append("LOWER(severity) = ?")
            params.append(severity.strip().lower())

        if category and category.strip():
            where_clauses.append("LOWER(category) = ?")
            params.append(category.strip().lower())

        if search and search.strip():
            where_clauses.append("(title LIKE ? OR body LIKE ?)")
            s_param = f"%{search.strip()}%"
            params.extend([s_param, s_param])

        where_sql = " AND ".join(where_clauses)

        # Подсчет количества элементов с учетом фильтра
        count_cur = conn.execute(f"SELECT COUNT(*) FROM notifications WHERE {where_sql}", params)
        filtered_total = count_cur.fetchone()[0]

        table_info = conn.execute("PRAGMA table_info(notifications)").fetchall()
        has_group_col = any(col["name"] == "group_count" for col in table_info)
        has_actions_col = any(col["name"] == "actions" for col in table_info)
        has_ack_col = any(col["name"] == "acknowledged_at" for col in table_info)

        group_sql = "COALESCE(group_count, 1) as group_count" if has_group_col else "1 as group_count"
        actions_sql = ", actions" if has_actions_col else ", NULL as actions"
        ack_sql = ", acknowledged_at, acknowledged_by" if has_ack_col else ", NULL as acknowledged_at, NULL as acknowledged_by"

        # Получение элементов
        query_sql = f"""
            SELECT id, module_id, user_id, title, body, severity, category, entity_id, target_url, {group_sql}{actions_sql}{ack_sql}, created_at, read_at
            FROM notifications
            WHERE {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """
        cur = conn.execute(query_sql, params + [limit, offset])

        raw_items = [dict(row) for row in cur.fetchall()]
        items = []
        for item in raw_items:
            if "actions" in item and item["actions"] and isinstance(item["actions"], str):
                try:
                    item["actions"] = json.loads(item["actions"])
                except Exception:
                    item["actions"] = None
            items.append(item)

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
    user_str = str(user_id).strip()
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE notifications SET read_at = COALESCE(read_at, ?) WHERE id = ? AND user_id = ?",
                (now, notification_id, user_str),
            )
            res = cur.rowcount > 0
            if res:
                invalidate_unread_cache(user_str)
            return res
    finally:
        conn.close()


def mark_all_as_read(user_id: str) -> int:
    """Пометить все непрочитанные уведомления пользователя прочитанными."""
    now = time.time()
    user_str = str(user_id).strip()
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE notifications SET read_at = ? WHERE user_id = ? AND read_at IS NULL",
                (now, user_str),
            )
            count = cur.rowcount
            if count > 0:
                invalidate_unread_cache(user_str)
            return count
    finally:
        conn.close()


def acknowledge_notification(notification_id: int, user_id: str) -> bool:
    """Зафиксировать проработку / квитирование уведомления."""
    user_str = str(user_id).strip()
    now = time.time()
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE notifications SET acknowledged_at = COALESCE(acknowledged_at, ?), acknowledged_by = ? WHERE id = ? AND user_id = ?",
                (now, user_str, notification_id, user_str),
            )
            res = cur.rowcount > 0
            if res:
                invalidate_unread_cache(user_str)
            return res
    finally:
        conn.close()


def acknowledge_all_notifications(user_id: str) -> int:
    """Квитировать все неквитированные уведомления пользователя."""
    user_str = str(user_id).strip()
    now = time.time()
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE notifications SET acknowledged_at = ?, acknowledged_by = ? WHERE user_id = ? AND acknowledged_at IS NULL",
                (now, user_str, user_str),
            )
            count = cur.rowcount
            if count > 0:
                invalidate_unread_cache(user_str)
            return count
    finally:
        conn.close()


def delete_notification(notification_id: int, user_id: str) -> bool:
    """Удалить одно конкретное уведомление пользователя."""
    user_str = str(user_id).strip()
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM notifications WHERE id = ? AND user_id = ?",
                (notification_id, user_str),
            )
            res = cur.rowcount > 0
            if res:
                invalidate_unread_cache(user_str)
            return res
    finally:
        conn.close()


def clear_read_notifications(user_id: str) -> int:
    """Удалить все прочитанные уведомления пользователя."""
    user_str = str(user_id).strip()
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM notifications WHERE user_id = ? AND read_at IS NOT NULL",
                (user_str,),
            )
            count = cur.rowcount
            if count > 0:
                invalidate_unread_cache(user_str)
            return count
    finally:
        conn.close()


def prune_notifications(days: int = NOTIFICATION_RETENTION_DAYS) -> int:
    """Удалить уведомления старше указанного количества дней (retention).
    
    Сохраняет непрочитанные критические аварии (severity='error'),
    чтобы они не терялись при длительном отсутствии администратора.
    """
    cutoff = time.time() - (days * 86400.0)
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM notifications WHERE created_at < ? AND (read_at IS NOT NULL OR LOWER(severity) != 'error')",
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
