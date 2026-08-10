"""API роутер уведомлений пользователя."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query, status

from backend.core.auth import CurrentUser, get_current_user
from backend.core.exceptions import NotFoundError
from backend.core.notify import (
    clear_read_notifications,
    delete_notification,
    get_notification_categories,
    get_notification_modules,
    get_notification_preferences,
    get_user_notifications,
    mark_all_as_read,
    mark_as_read,
    set_notification_preferences,
)

_log = logging.getLogger("nms.api.notifications")

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationPreferencesUpdateRequest(BaseModel):
    push_enabled: Optional[bool] = None
    sound_enabled: Optional[bool] = None
    subscribed_modules: Optional[List[str]] = None
    module_rules: Optional[Dict[str, Dict[str, Any]]] = None


@router.get("/categories", response_model=List[str])
async def list_categories():
    """Получить список поддерживаемых категорий уведомлений."""
    return await asyncio.to_thread(get_notification_categories)


@router.get("/modules", response_model=List[Dict[str, str]])
async def list_modules():
    """Получить список всех модулей системы для подписки."""
    return await asyncio.to_thread(get_notification_modules)


@router.get("/preferences", response_model=Dict[str, Any])
async def get_preferences(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получить предпочтения уведомлений текущего пользователя."""
    return await asyncio.to_thread(get_notification_preferences, user_id=current_user.id)


@router.put("/preferences", response_model=Dict[str, Any])
async def update_preferences(
    body: NotificationPreferencesUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Обновить предпочтения уведомлений текущего пользователя."""
    return await asyncio.to_thread(
        set_notification_preferences,
        user_id=current_user.id,
        push_enabled=body.push_enabled,
        sound_enabled=body.sound_enabled,
        subscribed_modules=body.subscribed_modules,
        module_rules=body.module_rules,
    )


@router.get("", response_model=Dict[str, Any])
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получить список своих уведомлений с количеством непрочитанных."""
    return await asyncio.to_thread(
        get_user_notifications,
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
    success = await asyncio.to_thread(mark_as_read, notification_id, user_id=current_user.id)
    if not success:
        raise NotFoundError(message="Notification not found", code="NOTIFICATION_NOT_FOUND")
    return {"status": "success", "id": notification_id}


@router.post("/read-all", response_model=Dict[str, Any])
async def read_all_notifications(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Пометить все непрочитанные уведомления текущего пользователя как прочитанные."""
    count = await asyncio.to_thread(mark_all_as_read, user_id=current_user.id)
    return {"status": "success", "marked_read_count": count}


@router.delete("/clear-read", response_model=Dict[str, Any])
async def delete_all_read(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Удалить все прочитанные уведомления пользователя."""
    count = await asyncio.to_thread(clear_read_notifications, user_id=current_user.id)
    return {"status": "success", "deleted_count": count}


@router.delete("/{notification_id}", response_model=Dict[str, Any])
async def remove_notification(
    notification_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Удалить одно конкретное уведомление."""
    success = await asyncio.to_thread(delete_notification, notification_id, user_id=current_user.id)
    if not success:
        raise NotFoundError(message="Notification not found", code="NOTIFICATION_NOT_FOUND")
    return {"status": "success", "id": notification_id}
