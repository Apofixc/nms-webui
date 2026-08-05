"""API роутер и функции для управления центром уведомлений NMS WebUI."""

import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user_optional
from backend.core.database import get_db_connection
from backend.core.events import broadcaster

_log = logging.getLogger("nms.notifications")

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str = "info"  # info, success, warning, error
    category: str = "system"  # system, stream, auth, audit
    link: Optional[str] = None


class NotificationItem(BaseModel):
    id: int
    title: str
    message: str
    type: str
    category: str
    read: bool
    link: Optional[str] = None
    created_at: str


def create_notification(
    title: str,
    message: str,
    notification_type: str = "info",
    category: str = "system",
    link: Optional[str] = None,
) -> dict:
    """Создать уведомление в БД и разослать всем сокет-клиентам."""
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO notifications (title, message, type, category, link)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, message, notification_type, category, link),
            )
            notification_id = cur.lastrowid
            row = conn.execute(
                "SELECT id, title, message, type, category, read, link, created_at FROM notifications WHERE id = ?",
                (notification_id,),
            ).fetchone()
            notification_dict = dict(row)
            notification_dict["read"] = bool(notification_dict["read"])

        # Вещание через WebSocket
        payload = {
            "type": "notification_created",
            "notification": notification_dict,
        }
        broadcaster.broadcast(json.dumps(payload), payload)

        return notification_dict
    except Exception as exc:
        _log.error("Failed to create notification: %s", exc)
        return {}
    finally:
        conn.close()


@router.get("", response_model=List[NotificationItem])
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Получить список уведомлений."""
    conn = get_db_connection()
    try:
        query = "SELECT id, title, message, type, category, read, link, created_at FROM notifications"
        params = []
        if unread_only:
            query += " WHERE read = 0"
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["read"] = bool(item["read"])
            result.append(item)
        return result
    finally:
        conn.close()


@router.get("/unread-count")
async def get_unread_count(
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Получить количество непрочитанных уведомлений."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT COUNT(*) as count FROM notifications WHERE read = 0").fetchone()
        return {"count": row["count"] if row else 0}
    finally:
        conn.close()


@router.post("", response_model=NotificationItem)
async def create_notification_endpoint(
    payload: NotificationCreate,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Создать новое уведомление (ручной/внутренний эндпоинт)."""
    item = create_notification(
        title=payload.title,
        message=payload.message,
        notification_type=payload.type,
        category=payload.category,
        link=payload.link,
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification",
        )
    return item


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Отметить конкретное уведомление как прочитанное."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE notifications SET read = 1 WHERE id = ?",
                (notification_id,),
            )
        return {"status": "ok", "id": notification_id}
    finally:
        conn.close()


@router.post("/read-all")
async def mark_all_as_read(
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Отметить все уведомления как прочитанные."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("UPDATE notifications SET read = 1 WHERE read = 0")
        return {"status": "ok"}
    finally:
        conn.close()


@router.delete("/clear")
async def clear_notifications(
    unread_only: bool = False,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Очистить уведомления."""
    conn = get_db_connection()
    try:
        with conn:
            if unread_only:
                conn.execute("DELETE FROM notifications WHERE read = 1")
            else:
                conn.execute("DELETE FROM notifications")
        return {"status": "ok"}
    finally:
        conn.close()


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Удалить конкретное уведомление."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
        return {"status": "ok", "id": notification_id}
    finally:
        conn.close()
