"""Агрегированные эндпоинты мониторинга."""
from fastapi import APIRouter

from backend.modules.astra.services.aggregator import (
    aggregated_health,
    aggregated_channels_stats,
)
from backend.modules.astra.services.health_checker import get_status


def router_factory() -> APIRouter:
    router = APIRouter()

    @router.get("/api/aggregate/health")
    async def get_aggregate_health():
        return await aggregated_health()

    @router.get("/api/aggregate/stats")
    async def get_aggregate_stats():
        return await aggregated_channels_stats()

    @router.get("/api/monitoring/status")
    async def monitoring_status():
        return get_status()

    return router
