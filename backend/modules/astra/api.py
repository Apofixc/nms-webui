import logging
from typing import Any
from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.core.config import (
    load_instances,
    save_instances,
    add_instance,
    remove_instance_by_index,
    get_instance_by_id,
    InstanceConfig,
)
from backend.core.plugin.registry import get_instance
from .models import InstanceAdd, InstanceUpdate
from .services import AstraClient

_log = logging.getLogger("nms.astra.api")


def router(ctx) -> APIRouter:
    """Фабрика для создания роутера модуля astra."""
    r = APIRouter(prefix="/api/v1/m/astra", tags=["astra"])

    def get_module() -> Any:
        module = get_instance("astra")
        if module is None:
            raise HTTPException(status_code=503, detail="Astra module not loaded")
        return module

    @r.get("/instances")
    async def list_instances():
        """Получить список экземпляров с их текущим статусом доступности."""
        module = get_module()
        configs = load_instances()
        result = []
        for idx, cfg in enumerate(configs):
            key = f"{cfg.host}:{cfg.port}"
            cache_info = module.cache.get(key) or {}
            result.append(
                {
                    "index": idx,
                    "host": cfg.host,
                    "port": cfg.port,
                    "api_key": cfg.api_key,
                    "label": cfg.label or f"Astra {cfg.host}:{cfg.port}",
                    "online": cache_info.get("online", False),
                    "last_seen": cache_info.get("last_seen", 0),
                    "error": cache_info.get("error"),
                    "version": cache_info.get("snapshot", {})
                    .get("system", {})
                    .get("astra_version", "N/A"),
                }
            )
        return {"items": result}

    @r.post("/instances")
    async def create_instance(body: InstanceAdd):
        """Добавить новый экземпляр Astra."""
        try:
            add_instance(
                host=body.host,
                port=body.port,
                api_key=body.api_key,
                label=body.label,
            )
            return {"ok": True}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @r.put("/instances/{index}")
    async def update_instance(index: int, body: InstanceUpdate):
        """Обновить настройки существующего экземпляра."""
        configs = load_instances()
        if index < 0 or index >= len(configs):
            raise HTTPException(status_code=404, detail="Instance not found")

        cfg = configs[index]
        if body.host is not None:
            cfg.host = body.host
        if body.port is not None:
            cfg.port = body.port
        if body.api_key is not None:
            cfg.api_key = body.api_key
        if body.label is not None:
            cfg.label = body.label

        save_instances(configs)
        return {"ok": True}

    @r.delete("/instances/{index}")
    async def delete_instance(index: int):
        """Удалить экземпляр Astra."""
        if not remove_instance_by_index(index):
            raise HTTPException(status_code=404, detail="Instance not found")
        return {"ok": True}

    @r.post("/instances/{index}/reload")
    async def reload_instance_config(index: int):
        """Перезагрузить конфигурацию Astra на инстансе."""
        res = get_instance_by_id(index)
        if not res:
            raise HTTPException(status_code=404, detail="Instance not found")
        cfg, _ = res
        client = AstraClient(cfg.host, cfg.port, cfg.api_key)
        try:
            await client.reload_config()
            return {"ok": True, "detail": "Reload command sent"}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    @r.get("/monitoring/summary")
    async def monitoring_summary():
        """Агрегированный дашборд состояния по всем инстансам."""
        module = get_module()
        configs = load_instances()

        total_instances = len(configs)
        online_instances = 0
        total_channels = 0
        ready_channels = 0
        total_adapters = 0
        active_adapters = 0

        latest_history = {}
        all_events = []

        for idx, cfg in enumerate(configs):
            key = f"{cfg.host}:{cfg.port}"
            cache_info = module.cache.get(key) or {}
            history_info = module.history.get(key) or []
            latest_history[key] = history_info

            if cache_info.get("online"):
                online_instances += 1
                snapshot = cache_info.get("snapshot") or {}

                # Подсчет каналов
                channels = snapshot.get("channels") or []
                total_channels += len(channels)
                ready_channels += sum(
                    1 for c in channels if c.get("ready", False)
                )

                # Подсчет адаптеров
                adapters = snapshot.get("adapters") or []
                total_adapters += len(adapters)
                active_adapters += sum(
                    1 for a in adapters if a.get("status", {}).get("lock", False)
                )

                # Сбор событий
                events = snapshot.get("events") or []
                for ev in events:
                    all_events.append(
                        {
                            "time": ev.get("time", 0),
                            "level": ev.get("level", "info"),
                            "context": ev.get("context", "system"),
                            "message": ev.get("message", ""),
                            "instance_index": idx,
                            "instance_label": cfg.label
                            or f"{cfg.host}:{cfg.port}",
                        }
                    )

        all_events.sort(key=lambda e: e["time"], reverse=True)

        return {
            "instances_total": total_instances,
            "instances_online": online_instances,
            "channels_total": total_channels,
            "channels_ready": ready_channels,
            "adapters_total": total_adapters,
            "adapters_active": active_adapters,
            "history": latest_history,
            "events": all_events[:50],
        }

    @r.get("/monitoring/channels")
    async def monitoring_channels():
        """Список каналов со всех инстансов."""
        module = get_module()
        configs = load_instances()
        result = []

        for idx, cfg in enumerate(configs):
            key = f"{cfg.host}:{cfg.port}"
            cache_info = module.cache.get(key) or {}
            if cache_info.get("online"):
                snapshot = cache_info.get("snapshot") or {}
                channels = snapshot.get("channels") or []
                for chan in channels:
                    result.append(
                        {
                            "instance_index": idx,
                            "instance_label": cfg.label
                            or f"{cfg.host}:{cfg.port}",
                            "name": chan.get("name"),
                            "ready": chan.get("ready", False),
                            "scrambled": chan.get("scrambled", False),
                            "bitrate": chan.get("bitrate", 0),
                            "cc_errors": chan.get("cc_errors", 0),
                            "pes_errors": chan.get("pes_errors", 0),
                            "inputs": chan.get("config", {}).get("input", []),
                            "outputs": chan.get("config", {}).get("output", []),
                        }
                    )
        return {"items": result}

    @r.post("/monitoring/channels/{instance_index}/{channel_name}/{action}")
    async def control_channel(
        instance_index: int, channel_name: str, action: str
    ):
        """Управление состоянием канала (stop / restart / delete)."""
        res = get_instance_by_id(instance_index)
        if not res:
            raise HTTPException(status_code=404, detail="Instance not found")
        cfg, _ = res
        client = AstraClient(cfg.host, cfg.port, cfg.api_key)

        try:
            if action == "stop":
                resp = await client.stop_channel(channel_name)
            elif action == "restart":
                resp = await client.restart_channel(channel_name)
            elif action == "delete":
                resp = await client.delete_channel(channel_name)
            else:
                raise HTTPException(status_code=400, detail="Invalid action")
            return {"ok": True, "response": resp}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    @r.get("/monitoring/adapters")
    async def monitoring_adapters():
        """Список DVB-адаптеров со всех инстансов."""
        module = get_module()
        configs = load_instances()
        result = []

        for idx, cfg in enumerate(configs):
            key = f"{cfg.host}:{cfg.port}"
            cache_info = module.cache.get(key) or {}
            if cache_info.get("online"):
                snapshot = cache_info.get("snapshot") or {}
                adapters = snapshot.get("adapters") or []
                for adap in adapters:
                    status = adap.get("status") or {}
                    result.append(
                        {
                            "instance_index": idx,
                            "instance_label": cfg.label
                            or f"{cfg.host}:{cfg.port}",
                            "name": adap.get("name", "DVB Adapter"),
                            "adapter_id": adap.get("adapter"),
                            "type": adap.get("type", "unknown"),
                            "lock": status.get("lock", False),
                            "signal": status.get("signal", 0),
                            "snr": status.get("snr", 0),
                            "ber": status.get("ber", 0),
                            "unc": status.get("unc", 0),
                        }
                    )
        return {"items": result}

    @r.post("/monitoring/adapters/{instance_index}/{adapter_name}/scan")
    async def scan_adapter(instance_index: int, adapter_name: str):
        """Запустить сканирование DVB-адаптера."""
        res = get_instance_by_id(instance_index)
        if not res:
            raise HTTPException(status_code=404, detail="Instance not found")
        cfg, _ = res
        client = AstraClient(cfg.host, cfg.port, cfg.api_key)

        try:
            resp = await client.scan_adapter_channels(adapter_name)
            return {"ok": True, "response": resp}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    @r.get("/monitoring/adapters/{instance_index}/{adapter_name}/scan-result")
    async def get_scan_result(instance_index: int, adapter_name: str):
        """Получить результаты сканирования."""
        res = get_instance_by_id(instance_index)
        if not res:
            raise HTTPException(status_code=404, detail="Instance not found")
        cfg, _ = res
        client = AstraClient(cfg.host, cfg.port, cfg.api_key)

        try:
            resp = await client.get_adapter_scan_result(adapter_name)
            return resp
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    return r
