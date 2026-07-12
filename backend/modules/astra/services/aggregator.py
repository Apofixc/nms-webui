"""Агрегация данных со всех инстансов Astra (параллельный опрос)."""
from __future__ import annotations

import asyncio
from typing import Any

from backend.core.config import load_instances, get_instance_by_id, get_settings
from backend.core.plugin.registry import get_module_settings
from backend.modules.astra.utils.astra_client import AstraClient


def _client(instance_id: int) -> AstraClient | None:
    pair = get_instance_by_id(instance_id)
    if not pair:
        return None
    cfg, base = pair
    mod_settings = get_module_settings("astra")
    timeout = mod_settings.get("timeout", get_settings().request_timeout)
    return AstraClient(base, api_key=cfg.api_key, timeout=timeout)


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
    inst = instances[instance_id] if instance_id < len(instances) else None
    port = inst.port if inst else 0
    host = inst.host if inst else "127.0.0.1"
    return [
        {**ch, "instance_id": instance_id, "instance_port": port, "instance_host": host}
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


async def fetch_snapshot(instance_id: int) -> dict:
    """Один запрос вместо 5-6: /api/snapshot astra-monitor."""
    instances = load_instances()
    cfg = instances[instance_id] if instance_id < len(instances) else None
    base = {
        "instance_id": instance_id,
        "port": cfg.port if cfg else 0,
        "label": (cfg.label or f"{cfg.host}:{cfg.port}") if cfg else str(instance_id),
    }
    c = _client(instance_id)
    if not c:
        return {**base, "status": "invalid", "data": None}
    code, data = await c.get_snapshot()
    if code == 200 and isinstance(data, dict):
        return {**base, "status": "healthy", "instance": data.get("instance"), "data": data}
    if code == 404:
        # старая версия astra-monitor без /api/snapshot
        return {**base, "status": "unsupported", "data": None}
    return {**base, "status": "unreachable", "data": data}


async def aggregated_snapshot() -> dict:
    instances = load_instances()
    if not instances:
        return {"instances": []}
    results = await asyncio.gather(*[fetch_snapshot(i) for i in range(len(instances))])
    return {"instances": list(results)}


async def fetch_events(instance_id: int) -> list[dict]:
    c = _client(instance_id)
    if not c:
        return []
    code, data = await c.get_events()
    if code != 200 or not isinstance(data, list):
        return []
    return [
        {**ev, "instance_id": instance_id}
        for ev in data
        if isinstance(ev, dict)
    ]


async def aggregated_events() -> dict:
    instances = load_instances()
    if not instances:
        return {"events": []}
    results = await asyncio.gather(*[fetch_events(i) for i in range(len(instances))])
    events: list[dict] = []
    for ev_list in results:
        events.extend(ev_list)
    events.sort(key=lambda ev: ev.get("time", 0))
    return {"events": events}


async def aggregated_channels_stats() -> dict:
    instances = load_instances()
    total: dict[str, Any] = {
        "total_astra_channels": 0, "total_monitored": 0,
        "online": 0, "offline": 0, "with_errors": 0,
    }
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
        elif code == 200 and isinstance(data, list):
            # astra-monitor: список статусов мониторов каналов
            total["total_monitored"] += len(data)
            for st in data:
                if not isinstance(st, dict):
                    continue
                if st.get("ready"):
                    total["online"] += 1
                else:
                    total["offline"] += 1
                if st.get("cc_errors", 0) > 0 or st.get("pes_errors", 0) > 0:
                    total["with_errors"] += 1
            ch_code, ch_list = await c.get_channels()
            if ch_code == 200 and isinstance(ch_list, list):
                total["total_astra_channels"] += len(ch_list)
    return total
