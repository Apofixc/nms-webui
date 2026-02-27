"""Astra instances API: CRUD, scan, health-check, proxy."""
import asyncio

from fastapi import APIRouter, HTTPException

from backend.modules.astra.utils.astra_client import AstraClient
from backend.core.config import (
    load_instances,
    get_instance_by_id,
    get_settings,
    add_instance as config_add_instance,
    remove_instance_by_index,
)
from backend.modules.astra.services.aggregator import _client
from backend.modules.astra.services.health_checker import (
    get_status as health_checker_get_status,
    set_check_interval_sec,
    check_instances_immediately,
    clear_events,
    remove_event_at_index,
)


def router_factory() -> APIRouter:
    router = APIRouter()

    @router.get("/api/instances")
    async def list_instances():
        instances = load_instances()
        return [
            {"id": i, "host": c.host, "port": c.port, "label": c.label or f"{c.host}:{c.port}"}
            for i, c in enumerate(instances)
        ]

    @router.get("/api/instances/status")
    async def instances_status():
        return health_checker_get_status()

    @router.delete("/api/instances/status/events")
    async def clear_status_events():
        clear_events()
        return {"message": "events cleared"}

    @router.delete("/api/instances/status/events/{event_index}")
    async def delete_status_event(event_index: int):
        if not remove_event_at_index(event_index):
            raise HTTPException(404, detail="Event not found")
        return {"message": "event removed"}

    @router.post("/api/instances")
    async def create_instance(body: dict):
        host = body.get("host")
        port = body.get("port")
        if host is None or port is None:
            raise HTTPException(400, detail="host and port required")
        try:
            port = int(port)
        except (TypeError, ValueError):
            raise HTTPException(400, detail="port must be integer")
        api_key = body.get("api_key", "test")
        label = body.get("label") or None
        cfg = config_add_instance(host=host, port=port, api_key=api_key, label=label)
        result = {"id": len(load_instances()) - 1, "host": cfg.host, "port": cfg.port, "label": cfg.label or f"{cfg.host}:{cfg.port}"}
        await check_instances_immediately([result["id"]])
        return result

    @router.delete("/api/instances/{instance_id}")
    async def delete_instance(instance_id: int):
        if not remove_instance_by_index(instance_id):
            raise HTTPException(404, detail="Instance not found")
        return {"message": "deleted"}

    @router.post("/api/instances/scan")
    async def scan_instances(body: dict):
        host = body.get("host")
        port_start = body.get("port_start")
        port_end = body.get("port_end")
        if host is None or port_start is None or port_end is None:
            raise HTTPException(400, detail="host, port_start, port_end required")
        try:
            port_start, port_end = int(port_start), int(port_end)
        except (TypeError, ValueError):
            raise HTTPException(400, detail="port_start and port_end must be integers")
        if port_start > port_end or port_end - port_start > 1000:
            raise HTTPException(400, detail="port range too large (max 1000)")
        api_key = body.get("api_key", "test")
        timeout = get_settings().request_timeout

        async def check_port(port: int):
            base = f"http://{host}:{port}"
            client = AstraClient(base, api_key=api_key, timeout=min(3.0, timeout))
            code, data = await client.health()
            return port if (code == 200 and data and "_error" not in data) else None

        ports = list(range(port_start, port_end + 1))
        results = await asyncio.gather(*[check_port(p) for p in ports], return_exceptions=True)
        found = [r for r in results if isinstance(r, int) and r is not None]
        n_before = len(load_instances())
        added = []
        for port in found:
            cfg = config_add_instance(host=host, port=port, api_key=api_key, label=None)
            added.append({"host": cfg.host, "port": cfg.port, "label": cfg.label or f"{cfg.host}:{cfg.port}"})
        new_ids = list(range(n_before, len(load_instances())))
        if new_ids:
            await check_instances_immediately(new_ids)
        return {"found": found, "added": added}

    @router.get("/api/instances/{instance_id}/health")
    async def instance_health(instance_id: int):
        pair = get_instance_by_id(instance_id)
        if not pair:
            raise HTTPException(404, "Instance not found")
        cfg, base = pair
        client = AstraClient(base, api_key=cfg.api_key, timeout=get_settings().request_timeout)
        code, data = await client.health()
        if code == 0:
            raise HTTPException(502, detail=data.get("_error", "Unreachable"))
        if code >= 400:
            raise HTTPException(code, detail=data)
        return {"instance_id": instance_id, "port": cfg.port, "status": "healthy", "data": data}

    @router.get("/api/instances/{instance_id}/channels")
    async def proxy_channels(instance_id: int):
        c = _client(instance_id)
        if not c:
            raise HTTPException(404, "Instance not found")
        code, data = await c.get_channels()
        if code == 0:
            raise HTTPException(502, detail="Unreachable")
        if code >= 400:
            raise HTTPException(code, detail=data)
        return data if isinstance(data, list) else []

    @router.get("/api/instances/{instance_id}/monitors")
    async def proxy_monitors(instance_id: int):
        c = _client(instance_id)
        if not c:
            raise HTTPException(404, "Instance not found")
        code, data = await c.get_monitors()
        if code == 0:
            raise HTTPException(502, detail="Unreachable")
        if code >= 400:
            raise HTTPException(code, detail=data)
        return data if isinstance(data, list) else []

    return router
