"""NMS API: прокси и агрегация lib-monitor (Astra)."""
import asyncio
import sys
from pathlib import Path

# Корень проекта в path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.config import (
    load_instances,
    get_instance_by_id,
    get_settings,
    add_instance as config_add_instance,
    remove_instance_by_index,
)
from backend.astra_client import AstraClient
from backend.aggregator import aggregated_health, aggregated_channels, aggregated_channels_stats, _client
from backend.health_checker import (
    run_loop as health_checker_run,
    get_status as health_checker_get_status,
    set_check_interval_sec,
    check_instances_immediately,
    clear_events,
    remove_event_at_index,
)
from backend.telegraf_metrics import (
    update_from_telegraf_json,
    update_from_influx_line,
    get_snapshot as get_telegraf_snapshot,
)
from backend.stream import StreamFrameCapture, StreamPlaybackSession
from fastapi.responses import Response, FileResponse

_health_task: asyncio.Task | None = None
_stream_capture: StreamFrameCapture | None = None
_playback_sessions: dict[str, StreamPlaybackSession] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _health_task, _stream_capture, _playback_sessions
    load_instances()
    _stream_capture = StreamFrameCapture()
    _health_task = asyncio.create_task(health_checker_run())
    yield
    for sess in _playback_sessions.values():
        sess.stop()
    _playback_sessions.clear()
    if _health_task and not _health_task.done():
        _health_task.cancel()
        try:
            await _health_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="NMS API — lib-monitor", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/")
async def root():
    return {"service": "NMS API", "docs": "/docs"}


# --- Системные метрики (Telegraf push) ---
@app.post("/api/system/metrics")
async def receive_telegraf_metrics(request: Request):
    """Принять метрики от Telegraf (push). Тело: JSON (data_format=json) или Influx line protocol (data_format=influx)."""
    content_type = request.headers.get("content-type", "")
    body = await request.body()
    try:
        if "application/json" in content_type:
            import json
            data = json.loads(body.decode("utf-8"))
            update_from_telegraf_json(data)
        else:
            update_from_influx_line(body.decode("utf-8"))
    except Exception:
        pass
    return {"message": "ok"}


@app.get("/api/system/info")
async def system_info():
    """Последний снимок системных метрик (от Telegraf). Данные по запросу при открытии вкладки."""
    return get_telegraf_snapshot()


# --- Список инстансов ---
@app.get("/api/instances")
async def list_instances():
    instances = load_instances()
    return [
        {"id": i, "host": c.host, "port": c.port, "label": c.label or f"{c.host}:{c.port}"}
        for i, c in enumerate(instances)
    ]


@app.get("/api/instances/status")
async def instances_status():
    """Статусы доступности и последние события (down/recovered). Хранится до events_limit событий."""
    return health_checker_get_status()


@app.delete("/api/instances/status/events")
async def clear_status_events():
    """Очистить весь лог событий."""
    clear_events()
    return {"message": "events cleared"}


@app.delete("/api/instances/status/events/{event_index}")
async def delete_status_event(event_index: int):
    """Удалить одно событие по индексу (клик по сообщению)."""
    if not remove_event_at_index(event_index):
        raise HTTPException(404, detail="Event not found")
    return {"message": "event removed"}


@app.patch("/api/settings/check-interval")
async def patch_check_interval(body: dict):
    """Установить интервал проверки состояния инстансов (сек). body: { \"seconds\": 30 }."""
    sec = body.get("seconds")
    if sec is None:
        raise HTTPException(400, detail="seconds required")
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        raise HTTPException(400, detail="seconds must be integer")
    set_check_interval_sec(sec)
    return {"check_interval_sec": sec}


def _create_instance_impl(body: dict):
    """Общая логика добавления инстанса."""
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
    return {"id": len(load_instances()) - 1, "host": cfg.host, "port": cfg.port, "label": cfg.label or f"{cfg.host}:{cfg.port}"}


@app.post("/api/instances")
@app.post("/api/instances/")
async def create_instance(body: dict):
    """Ручное добавление инстанса. body: host, port, api_key?, label?"""
    result = _create_instance_impl(body)
    await check_instances_immediately([result["id"]])
    return result


@app.delete("/api/instances/{instance_id}")
async def delete_instance(instance_id: int):
    """Удалить инстанс из конфига по индексу."""
    if not remove_instance_by_index(instance_id):
        raise HTTPException(404, detail="Instance not found")
    return {"message": "deleted"}


@app.post("/api/instances/scan")
async def scan_instances(body: dict):
    """Сканирование портов. body: host, port_start, port_end, api_key?. Возвращает найденные и добавленные в конфиг."""
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


@app.get("/api/instances/{instance_id}/health")
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


# --- Агрегаты ---
@app.get("/api/aggregate/health")
async def get_aggregate_health():
    return await aggregated_health()


@app.get("/api/aggregate/channels")
async def get_aggregate_channels():
    return await aggregated_channels()


@app.get("/api/aggregate/channels/stats")
async def get_aggregate_channels_stats():
    return await aggregated_channels_stats()


# --- Скриншот и просмотр потоков (UDP/HTTP) ---
@app.get("/api/instances/{instance_id}/channels/preview")
async def channel_preview(instance_id: int, name: str):
    """Скриншот канала по instance_id и имени. Требует ffmpeg/vlc/gstreamer."""
    try:
        if _stream_capture is None or not _stream_capture.available():
            raise HTTPException(503, detail="No capture backend available (install ffmpeg)")
        data = await aggregated_channels()
        ch = next(
            (c for c in (data.get("channels") or []) if c.get("instance_id") == instance_id and c.get("name") == name),
            None,
        )
        if not ch:
            raise HTTPException(404, detail="Channel not found")
        outputs = ch.get("output") or []
        if not outputs:
            raise HTTPException(404, detail="Channel has no output URL")
        url = outputs[0]
        raw = await asyncio.to_thread(_stream_capture.capture, url, timeout_sec=10.0, output_format="jpeg")
        return Response(content=raw, media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=str(e))


@app.post("/api/streams/playback")
async def start_stream_playback(body: dict):
    """
    Запустить сессию просмотра. body: { "url": "udp://..." } или { "instance_id": int, "channel_name": str }.
    Возвращает playback_url для плеера (готовый http или /api/streams/{id}/playlist.m3u8).
    """
    try:
        url = body.get("url")
        if not url:
            instance_id = body.get("instance_id")
            channel_name = body.get("channel_name")
            if instance_id is None or not channel_name:
                raise HTTPException(400, detail="Provide 'url' or 'instance_id' and 'channel_name'")
            data = await aggregated_channels()
            ch = next(
                (c for c in (data.get("channels") or []) if c.get("instance_id") == instance_id and c.get("name") == channel_name),
                None,
            )
            if not ch:
                raise HTTPException(404, detail="Channel not found")
            outputs = ch.get("output") or []
            if not outputs:
                raise HTTPException(404, detail="Channel has no output URL")
            url = outputs[0]
        session = StreamPlaybackSession()
        playback_url = session.start(url)
        sid = session._session_id
        if sid:
            _playback_sessions[sid] = session
        return {"playback_url": playback_url, "session_id": sid}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=str(e))


@app.get("/api/streams/{session_id}/{path:path}")
async def stream_session_file(session_id: str, path: str):
    """Раздача HLS плейлиста и сегментов сессии просмотра."""
    session = _playback_sessions.get(session_id)
    if not session:
        raise HTTPException(404, detail="Session not found")
    session_dir = session.get_session_dir()
    if not session_dir:
        raise HTTPException(404, detail="Session dir not found")
    file_path = session_dir / path
    if not file_path.resolve().is_relative_to(session_dir.resolve()):
        raise HTTPException(403, detail="Invalid path")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, detail="File not found")
    media_type = "application/vnd.apple.mpegurl" if path.endswith(".m3u8") else "video/mp2t"
    return FileResponse(file_path, media_type=media_type)


@app.delete("/api/streams/playback/{session_id}")
async def stop_stream_playback(session_id: str):
    """Остановить сессию просмотра."""
    session = _playback_sessions.pop(session_id, None)
    if not session:
        raise HTTPException(404, detail="Session not found")
    session.stop()
    return {"message": "stopped"}


# --- Прокси к инстансу ---
def _proxy(instance_id: int):
    pair = get_instance_by_id(instance_id)
    if not pair:
        raise HTTPException(404, "Instance not found")
    return _client(instance_id)


@app.delete("/api/instances/{instance_id}/channels/kill")
async def proxy_channel_kill(instance_id: int, name: str, reboot: bool = False):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.channel_kill(name, reboot=reboot)
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {"message": "ok"}


@app.post("/api/instances/{instance_id}/channels")
async def proxy_channel_create(instance_id: int, body: dict):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.channel_create(body)
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {"message": "Channel created"}


@app.get("/api/instances/{instance_id}/channels/inputs")
async def proxy_channel_inputs(instance_id: int, name: str):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_channel_inputs(name)
    if code == 0:
        raise HTTPException(502, detail="Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data


@app.delete("/api/instances/{instance_id}/streams/kill")
async def proxy_stream_kill(instance_id: int, name: str, reboot: bool = False):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.stream_kill(name, reboot=reboot)
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {"message": "ok"}


@app.post("/api/instances/{instance_id}/streams")
async def proxy_stream_create(instance_id: int, body: dict):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.stream_create(body)
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {"message": "Stream and monitor created"}


@app.get("/api/instances/{instance_id}/monitors")
async def proxy_monitors(instance_id: int):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_monitors()
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data if isinstance(data, list) else []


@app.get("/api/instances/{instance_id}/monitors/status")
async def proxy_monitors_status(instance_id: int):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_monitors_status()
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {}


@app.get("/api/instances/{instance_id}/subscribers")
async def proxy_subscribers(instance_id: int):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_subscribers()
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data if isinstance(data, list) else []


@app.get("/api/instances/{instance_id}/dvb/adapters")
async def proxy_dvb_adapters(instance_id: int):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_dvb_adapters()
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data if isinstance(data, list) else []


@app.get("/api/instances/{instance_id}/system/network/interfaces")
async def proxy_system_network_interfaces(instance_id: int):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_system_network_interfaces()
    if code == 0:
        raise HTTPException(502, detail="Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {}


@app.get("/api/instances/{instance_id}/system/network/hostname")
async def proxy_system_network_hostname(instance_id: int):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_system_network_hostname()
    if code == 0:
        raise HTTPException(502, detail="Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {}


@app.post("/api/instances/{instance_id}/system/reload")
async def proxy_system_reload(instance_id: int, body: dict | None = None):
    """Перезагрузка Astra. body: { \"delay\": сек } (опционально)."""
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    delay = (body or {}).get("delay")
    delay = int(delay) if delay is not None else None
    code, data = await c.system_reload(delay_sec=delay)
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {"message": "reload scheduled"}


@app.post("/api/instances/{instance_id}/system/exit")
async def proxy_system_exit(instance_id: int, body: dict | None = None):
    """Выключение Astra. body: { \"delay\": сек } (опционально)."""
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    delay = (body or {}).get("delay")
    delay = int(delay) if delay is not None else None
    code, data = await c.system_exit(delay_sec=delay)
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {"message": "exit scheduled"}


@app.post("/api/instances/{instance_id}/system/clear-cache")
async def proxy_system_clear_cache(instance_id: int):
    """Очистка кэша системных метрик Astra."""
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.system_clear_cache()
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable"))
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {"message": "Metrics updated"}


@app.get("/api/instances/{instance_id}/utils/info")
async def proxy_utils_info(instance_id: int):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_utils_info()
    if code == 0:
        raise HTTPException(502, detail="Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=data)
    return data or {}
