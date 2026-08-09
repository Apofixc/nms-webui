"""API роутер уведомлений пользователя."""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, status

from backend.core.auth import CurrentUser, get_current_user
from backend.core.exceptions import NotFoundError
from backend.core.notify import (
    clear_read_notifications,
    delete_notification,
    get_user_notifications,
    mark_all_as_read,
    mark_as_read,
)

_log = logging.getLogger("nms.api.notifications")

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получить список своих уведомлений с количеством непрочитанных."""
    return get_user_notifications(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


@router.post("/{notification_id}/read", response_model=Dict[str, Any])
async def read_notification(
    notification_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Пометить конкретное уведомление как прочитанное."""
    success = mark_as_read(notification_id, user_id=current_user.id)
    if not success:
        raise NotFoundError(message="Notification not found or already read", code="NOTIFICATION_NOT_FOUND")
    return {"status": "success", "id": notification_id}


@router.post("/read-all", response_model=Dict[str, Any])
async def read_all_notifications(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Пометить все непрочитанные уведомления текущего пользователя как прочитанные."""
    count = mark_all_as_read(user_id=current_user.id)
    return {"status": "success", "marked_read_count": count}


@router.delete("/clear-read", response_model=Dict[str, Any])
async def delete_all_read(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Удалить все прочитанные уведомления пользователя."""
    count = clear_read_notifications(user_id=current_user.id)
    return {"status": "success", "deleted_count": count}


@router.delete("/{notification_id}", response_model=Dict[str, Any])
async def remove_notification(
    notification_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Удалить одно конкретное уведомление."""
    success = delete_notification(notification_id, user_id=current_user.id)
    if not success:
        raise NotFoundError(message="Notification not found", code="NOTIFICATION_NOT_FOUND")
    return {"status": "success", "id": notification_id}
