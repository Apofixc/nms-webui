"""API роутер уведомлений пользователя."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query, status

from backend.core.auth import CurrentUser, get_current_user
from backend.core.exceptions import NotFoundError
from backend.core.notify import (
    acknowledge_all_notifications,
    acknowledge_notification,
    clear_read_notifications,
    delete_notification,
    get_notification_categories,
    get_notification_modules,
    get_notification_preferences,
    get_user_notifications,
    mark_all_as_read,
    mark_as_read,
    prune_notifications,
    set_notification_preferences,
)

_log = logging.getLogger("nms.api.notifications")

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationPreferencesUpdateRequest(BaseModel):
    push_enabled: Optional[bool] = None
    sound_enabled: Optional[bool] = None
    subscribed_modules: Optional[List[str]] = None
    module_rules: Optional[Dict[str, Dict[str, Any]]] = None
    sound_signals: Optional[Dict[str, str]] = None
    muted_until: Optional[float] = None
    quiet_hours: Optional[Dict[str, Any]] = None


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
    fields_set = body.model_dump(exclude_unset=True)
    update_kwargs: Dict[str, Any] = {}
    for key in ["push_enabled", "sound_enabled", "subscribed_modules", "module_rules", "sound_signals", "muted_until", "quiet_hours"]:
        if key in fields_set:
            update_kwargs[key] = getattr(body, key)

    return await asyncio.to_thread(
        set_notification_preferences,
        user_id=current_user.id,
        **update_kwargs,
    )


@router.get("", response_model=Dict[str, Any])
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получить список своих уведомлений с фильтрацией и количеством непрочитанных."""
    return await asyncio.to_thread(
        get_user_notifications,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
        severity=severity,
        category=category,
        search=search,
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


@router.post("/{notification_id}/acknowledge", response_model=Dict[str, Any])
async def acknowledge_single_notification(
    notification_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Квитировать / зафиксировать проработку алерта."""
    success = await asyncio.to_thread(acknowledge_notification, notification_id, user_id=current_user.id)
    if not success:
        raise NotFoundError(message="Notification not found", code="NOTIFICATION_NOT_FOUND")
    return {"status": "success", "id": notification_id}


@router.post("/acknowledge-all", response_model=Dict[str, Any])
async def acknowledge_all_user_notifications(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Квитировать все неквитированные уведомления текущего пользователя."""
    count = await asyncio.to_thread(acknowledge_all_notifications, user_id=current_user.id)
    return {"status": "success", "acknowledged_count": count}


@router.post("/read-all", response_model=Dict[str, Any])
async def read_all_notifications(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Пометить все непрочитанные уведомления текущего пользователя как прочитанные."""
    now = time.time()
    count = await asyncio.to_thread(mark_all_as_read, user_id=current_user.id)
    return {"status": "success", "marked_read_count": count, "marked_at": now}


@router.delete("/clear-read", response_model=Dict[str, Any])
async def delete_all_read(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Удалить все прочитанные уведомления пользователя."""
    count = await asyncio.to_thread(clear_read_notifications, user_id=current_user.id)
    return {"status": "success", "deleted_count": count}


@router.post("/prune", response_model=Dict[str, Any])
async def prune_stale_notifications(
    days: int = Query(30, ge=1, le=365),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Очистить уведомления старше указанного количества дней."""
    count = await asyncio.to_thread(prune_notifications, days=days)
    return {"status": "success", "pruned_count": count}


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
