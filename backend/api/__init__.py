"""Единая точка входа для API роутеров NMS WebUI."""

from fastapi import APIRouter

from fastapi import APIRouter

from backend.api.events import router as events_router
from backend.api.modules import router as modules_router
from backend.api.notifications import router as notifications_router
from backend.api.system import router as system_router
from backend.api.users import router as users_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(system_router)
api_router.include_router(modules_router)
api_router.include_router(events_router)
api_router.include_router(notifications_router)

__all__ = [
    "api_router",
    "users_router",
    "system_router",
    "modules_router",
    "events_router",
    "notifications_router",
]



