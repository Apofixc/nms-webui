"""Фоновая проверка доступности инстансов и накопление событий."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from backend.core.config import load_instances, get_settings
from backend.core.plugin.registry import get_module_settings
from backend.modules.astra.utils.astra_client import AstraClient

# id -> { reachable, data, monitors_count, last_check }
_status_store: dict[int, dict] = {}
_events: list[dict] = []
_MAX_EVENTS = 15
_check_interval_sec: int | None = None


async def _check_one(instance_id: int) -> None:
    instances = load_instances()
    if instance_id >= len(instances):
        return
    cfg = instances[instance_id]
    mod_settings = get_module_settings("astra")
    timeout = mod_settings.get("timeout", get_settings().request_timeout)
    client = AstraClient(
        f"http://{cfg.host}:{cfg.port}",
        api_key=cfg.api_key,
        timeout=timeout,
    )
    code, data = await client.health()
    reachable = code == 200 and data and "_error" not in data
    monitors_count = 0
    if reachable:
        code2, mon = await client.get_monitors()
        if code2 == 200 and isinstance(mon, list):
            monitors_count = len(mon)
    now = datetime.now(timezone.utc).isoformat()
    prev = _status_store.get(instance_id, {})
    prev_reachable = prev.get("reachable")
    _status_store[instance_id] = {
        "reachable": reachable,
        "data": data if reachable else prev.get("data"),
        "monitors_count": monitors_count if reachable else prev.get("monitors_count", 0),
        "last_check": now,
    }
    if prev_reachable is not None and prev_reachable != reachable:
        event = {
            "instance_id": instance_id,
            "port": cfg.port,
            "label": cfg.label or f"{cfg.host}:{cfg.port}",
            "event": "recovered" if reachable else "down",
            "at": now,
        }
        _events.append(event)
        if len(_events) > _MAX_EVENTS:
            _events.pop(0)


async def run_loop() -> None:
    """Цикл проверки каждые 30 секунд (или по настройкам)."""
    while True:
        mod_settings = get_module_settings("astra")
        interval = mod_settings.get("ui_update_interval", 8)
        # В фоне проверяем в 2 раза реже, чем обновляется UI (минимум раз в 10 сек)
        bg_interval = max(10, interval * 2)
        instances = load_instances()
        n = len(instances)
        for i in list(_status_store):
            if i >= n:
                del _status_store[i]
        for i in range(n):
            try:
                await _check_one(i)
            except Exception:
                pass
        await asyncio.sleep(bg_interval)


async def check_instances_immediately(instance_ids: list[int]) -> None:
    if not instance_ids:
        return
    await asyncio.gather(*[_check_one(i) for i in instance_ids], return_exceptions=True)


def get_status() -> dict[str, Any]:
    instances = load_instances()
    out = []
    for i in range(len(instances)):
        cfg = instances[i]
        st = _status_store.get(i, {})
        out.append({
            "id": i,
            "host": cfg.host,
            "port": cfg.port,
            "label": cfg.label or f"{cfg.host}:{cfg.port}",
            "reachable": st.get("reachable"),
            "last_check": st.get("last_check"),
            "data": st.get("data"),
            "monitors_count": st.get("monitors_count"),
        })
    mod_settings = get_module_settings("astra")
    return {
        "instances": out,
        "events": list(_events),
        "events_limit": _MAX_EVENTS,
        "ui_update_interval": mod_settings.get("ui_update_interval", 8),
        "scan_host": mod_settings.get("scan_host", "127.0.0.1"),
        "scan_port_start": mod_settings.get("scan_port_start", 8000),
        "scan_port_end": mod_settings.get("scan_port_end", 8050),
        "default_api_key": mod_settings.get("default_api_key", "admin"),
    }


def clear_events() -> None:
    _events.clear()


def remove_event_at_index(index: int) -> bool:
    if 0 <= index < len(_events):
        _events.pop(index)
        return True
    return False
