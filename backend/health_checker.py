"""Фоновая проверка доступности инстансов и накопление событий (down/recovered)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from backend.config import load_instances, get_settings
from backend.astra_client import AstraClient

# id -> { reachable, data, monitors_count, last_check }
_status_store: dict[int, dict] = {}
# последние события для UI
_events: list[dict] = []
_MAX_EVENTS = 15
# интервал проверки (сек), None = из конфига
_check_interval_sec: int | None = None


async def _check_one(instance_id: int) -> None:
    instances = load_instances()
    if instance_id >= len(instances):
        return
    cfg = instances[instance_id]
    client = AstraClient(
        f"http://{cfg.host}:{cfg.port}",
        api_key=cfg.api_key,
        timeout=get_settings().request_timeout,
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


def get_check_interval_sec() -> int:
    """Текущий интервал проверки (сек)."""
    if _check_interval_sec is not None:
        return _check_interval_sec
    return getattr(get_settings(), "check_interval_sec", 30) or 30


def set_check_interval_sec(seconds: int) -> None:
    """Установить интервал проверки (сек). Действует до перезапуска."""
    global _check_interval_sec
    _check_interval_sec = max(5, min(600, seconds))


async def run_loop() -> None:
    """Цикл проверки каждые check_interval_sec секунд."""
    while True:
        interval = get_check_interval_sec()
        instances = load_instances()
        n = len(instances)
        # убрать из store индексы удалённых инстансов
        for i in list(_status_store):
            if i >= n:
                del _status_store[i]
        for i in range(n):
            try:
                await _check_one(i)
            except Exception:
                pass
        await asyncio.sleep(interval)


async def check_instances_immediately(instance_ids: list[int]) -> None:
    """Сразу проверить указанные инстансы (после добавления в конфиг)."""
    if not instance_ids:
        return
    await asyncio.gather(*[_check_one(i) for i in instance_ids], return_exceptions=True)


def get_status() -> dict[str, Any]:
    """Текущие статусы и последние события для API."""
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
    return {
        "instances": out,
        "events": list(_events),
        "events_limit": _MAX_EVENTS,
        "check_interval_sec": get_check_interval_sec(),
    }


def clear_events() -> None:
    """Очистить очередь событий."""
    global _events
    _events.clear()


def remove_event_at_index(index: int) -> bool:
    """Удалить одно событие по индексу. Возвращает True если удалено."""
    global _events
    if 0 <= index < len(_events):
        _events.pop(index)
        return True
    return False


def get_status_store() -> dict:
    """Для отладки."""
    return _status_store
