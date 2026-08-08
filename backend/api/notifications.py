"""API роутер и функции для управления центром уведомлений NMS WebUI."""

import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user_optional
from backend.core.database import get_db_connection
from backend.core.i18n import tr
from backend.core.exceptions import NMSError, NotFoundError, ValidationError
from backend.core.events import broadcaster

_log = logging.getLogger("nms.notifications")

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str = "info"  # info, success, warning, error
    category: str = "system"  # system, stream, auth, audit
    link: Optional[str] = None
    user_id: Optional[str] = None
    is_push: bool = False


class NotificationItem(BaseModel):
    id: int
    title: str
    message: str
    type: str
    category: str
    read: bool
    link: Optional[str] = None
    user_id: Optional[str] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    is_push: bool = False
    created_at: str


class NotificationReadBatchPayload(BaseModel):
    ids: List[int]


def create_notification(
    title: str,
    message: str,
    notification_type: str = "info",
    category: str = "system",
    link: Optional[str] = None,
    user_id: Optional[str] = None,
    is_push: bool = False,
) -> dict:
    """Создать уведомление в БД (или обновить существующее недавнее) и разослать сокет-клиентам."""
    conn = get_db_connection()
    try:
        with conn:
            # Дедупликация: проверяем наличие идентичного непрочитанного уведомления за последние 60 секунд
            existing = conn.execute(
                """
                SELECT id FROM notifications
                WHERE title = ? AND message = ? AND category = ? AND read = 0
                  AND (user_id IS ? OR user_id = ?)
                  AND created_at >= datetime('now', '-60 seconds')
                ORDER BY id DESC LIMIT 1
                """,
                (title, message, category, user_id, user_id),
            ).fetchone()

            if existing:
                notification_id = existing["id"]
                conn.execute(
                    "UPDATE notifications SET created_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (notification_id,),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO notifications (title, message, type, category, link, user_id, is_push)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (title, message, notification_type, category, link, user_id, 1 if is_push else 0),
                )
                notification_id = cur.lastrowid

            row = conn.execute(
                "SELECT id, title, message, type, category, read, link, user_id, acknowledged, acknowledged_by, acknowledged_at, is_push, created_at FROM notifications WHERE id = ?",
                (notification_id,),
            ).fetchone()
            notification_dict = dict(row)
            notification_dict["read"] = bool(notification_dict["read"])
            notification_dict["acknowledged"] = bool(notification_dict.get("acknowledged", False))
            notification_dict["is_push"] = bool(notification_dict.get("is_push", False))

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
    search: Optional[str] = None,
    category: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Получить список уведомлений с поддержкой полнотекстового поиска и фильтрации."""
    conn = get_db_connection()
    try:
        query = "SELECT id, title, message, type, category, read, link, user_id, acknowledged, acknowledged_by, acknowledged_at, is_push, created_at FROM notifications WHERE 1=1"
        params = []
        
        if user and hasattr(user, "id") and user.id:
            query += " AND (user_id IS NULL OR user_id = ?)"
            params.append(str(user.id))
        else:
            query += " AND user_id IS NULL"
            
        if unread_only:
            query += " AND read = 0"

        if category:
            query += " AND category = ?"
            params.append(category)

        if type:
            query += " AND type = ?"
            params.append(type)

        if search and search.strip():
            query += " AND (title LIKE ? OR message LIKE ?)"
            pattern = f"%{search.strip()}%"
            params.extend([pattern, pattern])
            
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["read"] = bool(item["read"])
            item["acknowledged"] = bool(item.get("acknowledged", False))
            item["is_push"] = bool(item.get("is_push", False))
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
        query = "SELECT COUNT(*) as count FROM notifications WHERE read = 0"
        params = []
        if user and hasattr(user, "id") and user.id:
            query += " AND (user_id IS NULL OR user_id = ?)"
            params.append(str(user.id))
        else:
            query += " AND user_id IS NULL"
            
        row = conn.execute(query, params).fetchone()
        return {"count": row["count"] if row else 0}
    finally:
        conn.close()


@router.post("", response_model=NotificationItem)
async def create_notification_endpoint(
    payload: NotificationCreate,
    request: Request,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Создать новое уведомление (ручной/внутренний эндпоинт)."""
    target_user_id = payload.user_id
    item = create_notification(
        title=payload.title,
        message=payload.message,
        notification_type=payload.type,
        category=payload.category,
        link=payload.link,
        user_id=target_user_id,
    )
    if not item:
        raise NMSError(message=tr(request, "notif_create_failed"), status_code=500, code="NOTIF_CREATE_FAILED")
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
            if user and hasattr(user, "id") and user.id:
                conn.execute(
                    "UPDATE notifications SET read = 1 WHERE id = ? AND (user_id IS NULL OR user_id = ?)",
                    (notification_id, str(user.id)),
                )
            else:
                conn.execute(
                    "UPDATE notifications SET read = 1 WHERE id = ? AND user_id IS NULL",
                    (notification_id,),
                )
        return {"status": "ok", "id": notification_id}
    finally:
        conn.close()


@router.post("/{notification_id}/unread")
async def mark_as_unread(
    notification_id: int,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Отметить конкретное уведомление как непрочитанное."""
    conn = get_db_connection()
    try:
        with conn:
            if user and hasattr(user, "id") and user.id:
                conn.execute(
                    "UPDATE notifications SET read = 0 WHERE id = ? AND (user_id IS NULL OR user_id = ?)",
                    (notification_id, str(user.id)),
                )
            else:
                conn.execute(
                    "UPDATE notifications SET read = 0 WHERE id = ? AND user_id IS NULL",
                    (notification_id,),
                )
        return {"status": "ok", "id": notification_id}
    finally:
        conn.close()



@router.post("/read-all")
async def mark_all_as_read(
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Отметить все доступные пользователю уведомления как прочитанные."""
    conn = get_db_connection()
    try:
        with conn:
            if user and hasattr(user, "id") and user.id:
                conn.execute(
                    "UPDATE notifications SET read = 1 WHERE read = 0 AND (user_id IS NULL OR user_id = ?)",
                    (str(user.id),),
                )
            else:
                conn.execute("UPDATE notifications SET read = 1 WHERE read = 0 AND user_id IS NULL")
        return {"status": "ok"}
    finally:
        conn.close()


@router.post("/read-batch")
async def mark_read_batch(
    payload: NotificationReadBatchPayload,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Отметить выбранную группу уведомлений как прочитанные."""
    if not payload.ids:
        return {"status": "ok", "updated": 0}
    conn = get_db_connection()
    try:
        with conn:
            placeholders = ",".join("?" * len(payload.ids))
            if user and hasattr(user, "id") and user.id:
                query = f"UPDATE notifications SET read = 1 WHERE id IN ({placeholders}) AND (user_id IS NULL OR user_id = ?)"
                params = list(payload.ids) + [str(user.id)]
            else:
                query = f"UPDATE notifications SET read = 1 WHERE id IN ({placeholders}) AND user_id IS NULL"
                params = list(payload.ids)
            cur = conn.execute(query, params)
            updated_count = cur.rowcount
        return {"status": "ok", "updated": updated_count}
    finally:
        conn.close()


@router.post("/{notification_id}/ack")
async def acknowledge_notification(
    notification_id: int,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Подтвердить/принять аварию или уведомление в работу (Acknowledge)."""
    conn = get_db_connection()
    try:
        ack_by = getattr(user, "username", None) or getattr(user, "id", "operator") if user else "system"
        with conn:
            if user and hasattr(user, "id") and user.id:
                conn.execute(
                    """
                    UPDATE notifications
                    SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND (user_id IS NULL OR user_id = ?)
                    """,
                    (str(ack_by), notification_id, str(user.id)),
                )
            else:
                conn.execute(
                    """
                    UPDATE notifications
                    SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id IS NULL
                    """,
                    (str(ack_by), notification_id),
                )

            row = conn.execute(
                "SELECT id, title, message, type, category, read, link, user_id, acknowledged, acknowledged_by, acknowledged_at, created_at FROM notifications WHERE id = ?",
                (notification_id,),
            ).fetchone()

        if row:
            item_dict = dict(row)
            item_dict["read"] = bool(item_dict["read"])
            item_dict["acknowledged"] = bool(item_dict["acknowledged"])
            payload = {
                "type": "notification_updated",
                "notification": item_dict,
            }
            broadcaster.broadcast(json.dumps(payload), payload)
            return item_dict

        return {"status": "ok", "id": notification_id}
    finally:
        conn.close()


@router.delete("/clear")
async def clear_notifications(
    unread_only: bool = False,
    days_old: Optional[int] = None,
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Очистить уведомления."""
    conn = get_db_connection()
    try:
        with conn:
            query = "DELETE FROM notifications WHERE 1=1"
            params = []
            
            if user and hasattr(user, "id") and user.id:
                query += " AND (user_id IS NULL OR user_id = ?)"
                params.append(str(user.id))
            else:
                query += " AND user_id IS NULL"

            if unread_only:
                query += " AND read = 1"

            if days_old and days_old > 0:
                query += " AND created_at <= datetime('now', '-' || ? || ' days')"
                params.append(days_old)

            conn.execute(query, params)
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
            if user and hasattr(user, "id") and user.id:
                conn.execute(
                    "DELETE FROM notifications WHERE id = ? AND (user_id IS NULL OR user_id = ?)",
                    (notification_id, str(user.id)),
                )
            else:
                conn.execute(
                    "DELETE FROM notifications WHERE id = ? AND user_id IS NULL",
                    (notification_id,),
                )
        return {"status": "ok", "id": notification_id}
    finally:
        conn.close()



