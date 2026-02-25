"""Модуль агрегирующих эндпоинтов (health, channels)."""
from fastapi import APIRouter

from backend.modules.astra.services.aggregator import (
    aggregated_channels,
    aggregated_channels_stats,
    aggregated_health,
)


def router_factory() -> APIRouter:
    router = APIRouter()

    @router.get("/api/aggregate/health")
    async def get_aggregate_health():
        return await aggregated_health()

    @router.get("/api/aggregate/channels")
    async def get_aggregate_channels():
        return await aggregated_channels()

    @router.get("/api/aggregate/channels/stats")
    async def get_aggregate_channels_stats():
        return await aggregated_channels_stats()

    return router
