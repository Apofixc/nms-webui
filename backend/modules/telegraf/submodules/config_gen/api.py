"""Telegraf config generation API."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from backend.modules.telegraf.submodules.config_gen.service import render_telegraf_config


def router_factory() -> APIRouter:
    router = APIRouter()

    @router.get("/api/telegraf/config", response_class=PlainTextResponse)
    async def get_telegraf_config(interval: str = "5s", metrics_url: str = "http://127.0.0.1:8000/api/system/metrics"):
        return render_telegraf_config(metrics_url=metrics_url, interval=interval)

    return router
