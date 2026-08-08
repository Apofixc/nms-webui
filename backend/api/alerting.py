"""API роутер для подсистемы внешнего алертинга (Alerting)."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user_optional
from backend.core.database import get_db_connection
from backend.core.i18n import tr
from backend.core.exceptions import NotFoundError, ValidationError
from backend.core.alerting import PROVIDERS, send_alert

_log = logging.getLogger("nms.alerting.api")

router = APIRouter(prefix="/api/alerting", tags=["alerting"])


class AlertChannelPayload(BaseModel):
    name: str
    type: str  # telegram, discord, viber, email, webhook, syslog
    enabled: bool = True
    min_type: str = "warning"
    categories: str = "*"
    config: dict


class AlertLogItem(BaseModel):
    id: int
    channel_id: str
    channel_type: str
    title: str
    message: str
    severity: str
    category: str
    success: bool
    error_message: Optional[str] = None
    retry_count: Optional[int] = 0
    suppressed: Optional[bool] = False
    created_at: str


class MaintenanceWindowPayload(BaseModel):
    name: str
    target_category: str = "*"
    starts_at: str
    ends_at: str
    enabled: bool = True


class EscalationRulePayload(BaseModel):
    name: str
    min_severity: str = "error"
    unack_timeout_sec: int = 900
    target_channel_id: str
    enabled: bool = True


@router.get("/channels")
async def get_channels():
    """Получить список всех каналов внешнего алертинга."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, type, enabled, min_type, categories, config, created_at FROM alert_channels ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["enabled"] = bool(item["enabled"])
            try:
                item["config"] = json.loads(item["config"])
            except Exception:
                item["config"] = {}
            result.append(item)
        return result
    finally:
        conn.close()


@router.post("/channels")
async def create_channel(payload: AlertChannelPayload):
    """Создать новый канал внешнего алертинга."""
    conn = get_db_connection()
    try:
        channel_id = f"channel-{uuid.uuid4().hex[:8]}"
        config_json = json.dumps(payload.config)
        with conn:
            conn.execute(
                """
                INSERT INTO alert_channels (id, name, type, enabled, min_type, categories, config)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    channel_id,
                    payload.name,
                    payload.type,
                    1 if payload.enabled else 0,
                    payload.min_type,
                    payload.categories,
                    config_json,
                ),
            )
        return {"status": "ok", "id": channel_id}
    finally:
        conn.close()


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: str, payload: AlertChannelPayload):
    """Обновить параметры канала алертинга."""
    conn = get_db_connection()
    try:
        config_json = json.dumps(payload.config)
        with conn:
            conn.execute(
                """
                UPDATE alert_channels
                SET name = ?, type = ?, enabled = ?, min_type = ?, categories = ?, config = ?
                WHERE id = ?
                """,
                (
                    payload.name,
                    payload.type,
                    1 if payload.enabled else 0,
                    payload.min_type,
                    payload.categories,
                    config_json,
                    channel_id,
                ),
            )
        return {"status": "ok", "id": channel_id}
    finally:
        conn.close()


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str):
    """Удалить канал алертинга."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM alert_channels WHERE id = ?", (channel_id,))
        return {"status": "ok", "id": channel_id}
    finally:
        conn.close()


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: str, request: Request):
    """Отправить тестовый алерт в выбранный канал связи."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id, name, type, config FROM alert_channels WHERE id = ?",
            (channel_id,),
        ).fetchone()
        if not row:
            raise NotFoundError(message=tr(request, "integration_not_found"), code="INTEGRATION_NOT_FOUND")

        c_type = row["type"].lower()
        try:
            config = json.loads(row["config"])
        except Exception:
            config = {}

        test_alert = {
            "title": tr(request, "test_integration_title", name=row["name"]),
            "message": tr(request, "test_integration_message"),
            "severity": "info",
            "category": "system",
        }

        provider = PROVIDERS.get(c_type)
        if not provider:
            raise ValidationError(message=tr(request, "unsupported_provider_type", c_type=c_type), code="UNSUPPORTED_PROVIDER_TYPE")

        res = provider(config, test_alert)
        ok = res[0] if isinstance(res, tuple) else bool(res)
        return {"status": "ok" if ok else "failed", "success": ok}
    finally:
        conn.close()


@router.get("/log", response_model=List[AlertLogItem])
async def get_alert_log(limit: int = 50, offset: int = 0):
    """Получить журнал истории отправки внешних алертов."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, channel_id, channel_type, title, message, severity, category, success, error_message, retry_count, suppressed, created_at
            FROM alert_log
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["success"] = bool(item["success"])
            item["suppressed"] = bool(item.get("suppressed", 0))
            result.append(item)
        return result
    finally:
        conn.close()


# ── Эндпоинты Maintenance Windows ─────────────────────────

@router.get("/maintenance")
async def get_maintenance_windows():
    """Получить список всех окон технического обслуживания."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, target_category, starts_at, ends_at, enabled, created_at FROM maintenance_windows ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["enabled"] = bool(item["enabled"])
            result.append(item)
        return result
    finally:
        conn.close()


@router.post("/maintenance")
async def create_maintenance_window(payload: MaintenanceWindowPayload):
    """Создать окно технического обслуживания."""
    conn = get_db_connection()
    try:
        mw_id = f"maint-{uuid.uuid4().hex[:8]}"
        with conn:
            conn.execute(
                """
                INSERT INTO maintenance_windows (id, name, target_category, starts_at, ends_at, enabled)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mw_id, payload.name, payload.target_category, payload.starts_at, payload.ends_at, 1 if payload.enabled else 0),
            )
        return {"status": "ok", "id": mw_id}
    finally:
        conn.close()


@router.delete("/maintenance/{mw_id}")
async def delete_maintenance_window(mw_id: str):
    """Удалить окно обслуживания."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM maintenance_windows WHERE id = ?", (mw_id,))
        return {"status": "ok", "id": mw_id}
    finally:
        conn.close()


# ── Эндпоинты Escalation Rules ──────────────────────────

@router.get("/escalations")
async def get_escalation_rules():
    """Получить правила эскалации неквитированных алертов."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, min_severity, unack_timeout_sec, target_channel_id, enabled, created_at FROM escalation_rules ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["enabled"] = bool(item["enabled"])
            result.append(item)
        return result
    finally:
        conn.close()


@router.post("/escalations")
async def create_escalation_rule(payload: EscalationRulePayload):
    """Создать новое правило эскалации."""
    conn = get_db_connection()
    try:
        rule_id = f"esc-{uuid.uuid4().hex[:8]}"
        with conn:
            conn.execute(
                """
                INSERT INTO escalation_rules (id, name, min_severity, unack_timeout_sec, target_channel_id, enabled)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (rule_id, payload.name, payload.min_severity, payload.unack_timeout_sec, payload.target_channel_id, 1 if payload.enabled else 0),
            )
        return {"status": "ok", "id": rule_id}
    finally:
        conn.close()


@router.delete("/escalations/{rule_id}")
async def delete_escalation_rule(rule_id: str):
    """Удалить правило эскалации."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM escalation_rules WHERE id = ?", (rule_id,))
        return {"status": "ok", "id": rule_id}
    finally:
        conn.close()

