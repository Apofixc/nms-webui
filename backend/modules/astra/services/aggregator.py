"""Агрегация данных со всех инстансов Astra (параллельный опрос)."""
from __future__ import annotations

import asyncio
from typing import Any

from backend.core.config import load_instances, get_instance_by_id, get_settings
from backend.modules.astra.utils.astra_client import AstraClient


def _client(instance_id: int) -> AstraClient | None:
    pair = get_instance_by_id(instance_id)
    if not pair:
        return None
    cfg, base = pair
    return AstraClient(base, api_key=cfg.api_key, timeout=get_settings().request_timeout)


async def fetch_health(instance_id: int) -> dict:
    c = _client(instance_id)
    if not c:
        return {"instance_id": instance_id, "status": "invalid", "data": None}
    code, data = await c.health()
    if code == 200 and data and "_error" not in data:
        return {"instance_id": instance_id, "status": "healthy", "data": data}
    return {"instance_id": instance_id, "status": "unreachable", "data": data}


async def fetch_channels(instance_id: int) -> tuple[list[dict], bool]:
    c = _client(instance_id)
    if not c:
        return [], True
    code, raw = await c.get_channels()
    if code != 200 or not isinstance(raw, list):
        return [], True
    instances = load_instances()
    port = instances[instance_id].port if instance_id < len(instances) else 0
    return [
        {**ch, "instance_id": instance_id, "instance_port": port}
        for ch in raw
    ], False


async def aggregated_health() -> dict:
    instances = load_instances()
    if not instances:
        return {"instances": []}
    results = await asyncio.gather(*[fetch_health(i) for i in range(len(instances))])
    out = []
    for i, r in enumerate(results):
        cfg = instances[i]
        out.append({
            "instance_id": i,
            "port": cfg.port,
            "label": cfg.label or f"{cfg.host}:{cfg.port}",
            "status": r["status"],
            "data": r["data"],
        })
    return {"instances": out}


async def aggregated_channels() -> dict:
    instances = load_instances()
    if not instances:
        return {"channels": [], "instances_unreachable": []}
    results = await asyncio.gather(*[fetch_channels(i) for i in range(len(instances))])
    channels = []
    unreachable = []
    for i, (ch_list, unreach) in enumerate(results):
        if unreach:
            unreachable.append(i)
        channels.extend(ch_list)
    return {"channels": channels, "instances_unreachable": unreachable}


async def aggregated_channels_stats() -> dict:
    instances = load_instances()
    total = {"total_astra_channels": 0, "total_monitored": 0, "online": 0, "offline": 0, "with_errors": 0}
    for i in range(len(instances)):
        c = _client(i)
        if not c:
            continue
        code, data = await c.get_channels_stats()
        if code == 200 and isinstance(data, dict):
            total["total_astra_channels"] += data.get("total_astra_channels", 0)
            total["total_monitored"] += data.get("total_monitored", 0)
            total["online"] += data.get("online", 0)
            total["offline"] += data.get("offline", 0)
            total["with_errors"] += data.get("with_errors", 0)
    return total
