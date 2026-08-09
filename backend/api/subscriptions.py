"""API роутер для управления подписками на уведомления (Ядро и Модули)."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.subscriptions import (
    create_subscription,
    delete_subscription,
    get_subscribable_sources,
    get_user_subscriptions,
    toggle_subscription,
    update_subscription,
)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


class SubscriptionCreatePayload(BaseModel):
    name: Optional[str] = ""
    source_type: str = "module"  # system, module
    module_id: str = "*"
    min_severity: str = "info"
    channels: List[str] = ["in_app"]
    mute_until: Optional[str] = None
    enabled: bool = True


class SubscriptionUpdatePayload(BaseModel):
    name: Optional[str] = None
    source_type: Optional[str] = None
    module_id: Optional[str] = None
    min_severity: Optional[str] = None
    channels: Optional[List[str]] = None
    mute_until: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("/sources")
async def list_sources(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    """Получить доступные источники подписок (Ядро NMS и подключаемые Модули)."""
    return get_subscribable_sources(request=request)


@router.get("")
async def list_subscriptions(user: CurrentUser = Depends(get_current_user)):
    """Получить список подписок текущего оператора."""
    return get_user_subscriptions(user.id)


@router.post("")
async def add_subscription(
    request: Request,
    payload: SubscriptionCreatePayload,
    user: CurrentUser = Depends(get_current_user),
):
    """Создать подписку на события ядра или конкретного модуля."""
    return create_subscription(
        user_id=user.id,
        name=payload.name or "",
        source_type=payload.source_type,
        module_id=payload.module_id,
        min_severity=payload.min_severity,
        channels=payload.channels,
        mute_until=payload.mute_until,
        enabled=payload.enabled,
        request=request,
    )


@router.put("/{sub_id}")
async def edit_subscription(
    sub_id: str,
    request: Request,
    payload: SubscriptionUpdatePayload,
    user: CurrentUser = Depends(get_current_user),
):
    """Обновить существующую подписку."""
    return update_subscription(
        sub_id=sub_id,
        user_id=user.id,
        name=payload.name,
        source_type=payload.source_type,
        module_id=payload.module_id,
        min_severity=payload.min_severity,
        channels=payload.channels,
        mute_until=payload.mute_until,
        enabled=payload.enabled,
        request=request,
    )


@router.delete("/{sub_id}")
async def remove_subscription(
    sub_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    """Удалить подписку."""
    success = delete_subscription(sub_id, user.id, request=request)
    return {"status": "ok", "deleted": success, "id": sub_id}


@router.post("/{sub_id}/toggle")
async def toggle_sub(
    sub_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    """Быстрое включение/отключение подписки."""
    return toggle_subscription(sub_id, user.id, request=request)
