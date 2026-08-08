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
    created_at: str


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

        ok = provider(config, test_alert)
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
            SELECT id, channel_id, channel_type, title, message, severity, category, success, error_message, created_at
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
            result.append(item)
        return result
    finally:
        conn.close()
