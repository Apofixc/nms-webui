"""Telegraf metrics API (push + snapshot)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Request

from backend.modules.telegraf.services.metrics_api import (
    get_snapshot,
    update_from_influx_line,
    update_from_telegraf_json,
)


def router_factory() -> APIRouter:
    router = APIRouter()

    @router.post("/api/system/metrics")
    async def receive_telegraf_metrics(request: Request):
        content_type = request.headers.get("content-type", "")
        body = await request.body()
        try:
            if "application/json" in content_type:
                update_from_telegraf_json(json.loads(body.decode("utf-8")))
            else:
                update_from_influx_line(body.decode("utf-8"))
        except Exception:
            pass
        return {"message": "ok"}

    @router.get("/api/system/info")
    async def system_info():
        return get_snapshot()

    @router.get("/api/telegraf/metrics/snapshot")
    async def telegraf_snapshot():
        return get_snapshot()

    return router
