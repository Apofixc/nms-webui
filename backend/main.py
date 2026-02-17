"""NMS API: прокси и агрегация lib-monitor (Astra)."""
import asyncio
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# Корень проекта в path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
from backend.stream import StreamFrameCapture, StreamPlaybackSession, TsAnalyzer
from backend.stream.capture import (
    get_available_capture_backends,
    get_capture_backends_for_setting,
    _backends_with_options,
)
from backend.stream.udp_to_http import stream_udp_to_http
from backend.stream.udp_to_http_backends import (
    UDP_TO_HTTP_BACKENDS_BY_NAME,
    get_available_udp_to_http_backends,
    get_udp_to_http_backend_chain,
)
from backend.utils import find_executable
from backend.webui_settings import (
    get_stream_capture_backend,
    get_stream_capture_backend_options,
    get_stream_capture_options,
    get_stream_playback_udp_backend,
    get_stream_playback_udp_backend_options,
    get_stream_playback_udp_output_format,
    get_webui_settings,
    save_webui_settings,
)
from fastapi.responses import Response, FileResponse, RedirectResponse, StreamingResponse

_health_task: asyncio.Task | None = None
_stream_capture: StreamFrameCapture | None = None
_playback_sessions: dict[str, StreamPlaybackSession] = {}
_queue = None  # rq.Queue, если задан NMS_REDIS_URL
_preview_refresh_job_id: str | None = None  # id текущей задачи обновления превью в RQ

# Кэш превью каналов: отдельная папка, загрузка при открытии вкладки и постепенное обновление
PREVIEW_CACHE_DIR = _root / "preview_cache"

# Лимиты тяжёлых операций: из конфига (NMS_HEAVY_*_GLOBAL=0 значит без лимита — для 1–2 пользователей).
# При большом числе пользователей задайте глобальные лимиты; per_ip защищает от одного клиента.
def _heavy_semaphores():
    s = get_settings()
    return (
        asyncio.Semaphore(s.heavy_preview_global) if s.heavy_preview_global else None,
        asyncio.Semaphore(s.heavy_analyze_global) if s.heavy_analyze_global else None,
        asyncio.Semaphore(s.heavy_playback_global) if s.heavy_playback_global else None,
    )

_HEAVY_PREVIEW_SEMAPHORE, _HEAVY_ANALYZE_SEMAPHORE, _HEAVY_PLAYBACK_SEMAPHORE = _heavy_semaphores()

_per_ip_lock = asyncio.Lock()
_per_ip_semaphores: dict[tuple[str, str], asyncio.Semaphore] = {}  # (kind, ip) -> Semaphore


def _client_ip(request: Request) -> str:
    return (request.client.host if request.client else "") or "unknown"


async def _per_ip_semaphore(kind: str, ip: str, limit: int) -> asyncio.Semaphore:
    key = (kind, ip)
    async with _per_ip_lock:
        if key not in _per_ip_semaphores:
            _per_ip_semaphores[key] = asyncio.Semaphore(limit)
        return _per_ip_semaphores[key]


@asynccontextmanager
async def _optional_sem(sem: asyncio.Semaphore | None):
    if sem is not None:
        async with sem:
            yield
    else:
        yield


def _preview_cache_path(instance_id: int, name: str) -> Path:
    """Безопасное имя файла для кэша превью по instance_id и имени канала."""
    safe = re.sub(r"[^\w\-.]", "_", f"{instance_id}_{name}")[:200].strip("_") or "channel"
    return PREVIEW_CACHE_DIR / f"{safe}.jpg"


def _normalize_stream_url(url: str, stream_host: str | None = None) -> str:
    """
    Нормализация URL потока из output канала.
    - Убирает фрагмент (#keep_active и т.п.).
    - Хост «0» заменяется на stream_host, если передан (хост инстанса Astra из конфига),
      иначе на 127.0.0.1 — чтобы бэкенд мог подключиться к потоку (та же машина или по сети).
    """
    if not url or not isinstance(url, str):
        return url
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return url
    netloc = parsed.netloc
    if netloc.startswith("0:") or netloc == "0":
        host = (stream_host or "127.0.0.1").strip()
        port_part = ":" + netloc.split(":", 1)[1] if ":" in netloc else ""
        netloc = host + port_part
    return urlunparse((scheme, netloc, parsed.path or "/", parsed.params, parsed.query, ""))


class SettingsPutBody(BaseModel):
    """Тело PUT /api/settings: только модули (вложенная структура)."""
    modules: dict[str, Any] | None = None


def _create_stream_capture_from_settings() -> StreamFrameCapture:
    """Создать StreamFrameCapture с бэкендами из настроек WebUI (модуль stream.capture)."""
    backend_classes = get_capture_backends_for_setting(get_stream_capture_backend())
    opts = get_stream_capture_backend_options()
    backends_with_opts = _backends_with_options(backend_classes, opts)
    return StreamFrameCapture(backends=backends_with_opts)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _health_task, _stream_capture, _playback_sessions, _queue
    load_instances()
    _stream_capture = _create_stream_capture_from_settings()
    _health_task = asyncio.create_task(health_checker_run())
    redis_url = get_settings().redis_url
    if redis_url:
        try:
            import redis
            from rq import Queue
            _queue = Queue(connection=redis.Redis.from_url(redis_url), name="nms", default_timeout=3600)
        except Exception:
            _queue = None
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


async def _refresh_preview_to_cache(instance_id: int, name: str) -> None:
    """Фоновое обновление превью в кэше (захват и запись в файл)."""
    if _stream_capture is None or not _stream_capture.available:
        return
    try:
        data = await aggregated_channels()
        ch = next(
            (c for c in (data.get("channels") or []) if c.get("instance_id") == instance_id and c.get("name") == name),
            None,
        )
        if not ch:
            return
        outputs = ch.get("output") or []
        if not outputs:
            return
        pair = get_instance_by_id(instance_id)
        stream_host = pair[0].host if pair else None
        url = _normalize_stream_url(outputs[0], stream_host)
        opts = get_stream_capture_options()
        async with _optional_sem(_HEAVY_PREVIEW_SEMAPHORE):
            raw = await asyncio.to_thread(
                _stream_capture.capture,
                url,
                timeout_sec=opts.get("timeout_sec", 10.0),
                output_format="jpeg",
                jpeg_quality=opts.get("jpeg_quality"),
            )
        cache_path = _preview_cache_path(instance_id, name)
        PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(raw)
    except Exception:
        pass


# --- Один цикл обновления превью при заходе на вкладку Каналы ---
_preview_refresh_running = False
_preview_refresh_done_at: float | None = None


async def _run_full_preview_refresh() -> None:
    """Один проход по всем каналам с output: обновить превью в кэше (in-process, если нет Redis)."""
    global _preview_refresh_running, _preview_refresh_done_at
    import time
    try:
        data = await aggregated_channels()
        channels = data.get("channels") or []
        with_output = [(c.get("instance_id"), c.get("name")) for c in channels if (c.get("output") or [])]
        for instance_id, name in with_output:
            if instance_id is None or not name:
                continue
            await _refresh_preview_to_cache(instance_id, name)
    except Exception:
        pass
    finally:
        _preview_refresh_running = False
        _preview_refresh_done_at = time.time()


def _build_preview_refresh_items(data: dict) -> list[dict]:
    """Список {url, cache_path} для воркера из aggregated channels."""
    channels = data.get("channels") or []
    items = []
    for c in channels:
        if not (c.get("output") or []):
            continue
        instance_id = c.get("instance_id")
        name = c.get("name")
        if instance_id is None or not name:
            continue
        pair = get_instance_by_id(instance_id)
        stream_host = pair[0].host if pair else None
        url = _normalize_stream_url((c.get("output") or [])[0], stream_host)
        cache_path = _preview_cache_path(instance_id, name)
        items.append({"url": url, "cache_path": str(cache_path.resolve())})
    return items


@app.post("/api/channels/preview-refresh/start")
async def channels_preview_refresh_start():
    """
    Запустить один цикл обновления превью в кэше (при заходе на вкладку Каналы).
    Если задан NMS_REDIS_URL — задача ставится в очередь RQ (воркер); иначе выполняется в процессе.
    """
    global _preview_refresh_running, _preview_refresh_job_id
    import time
    from backend import tasks as rq_tasks

    cooldown = get_settings().preview_refresh_cooldown_sec
    if _preview_refresh_running:
        return {"started": False, "reason": "already_running"}
    if _preview_refresh_done_at is not None and (time.time() - _preview_refresh_done_at) < cooldown:
        return {"started": False, "reason": "cooldown"}
    if _queue is not None:
        try:
            data = await aggregated_channels()
            items = _build_preview_refresh_items(data)
            if not items:
                return {"started": False, "reason": "no_channels"}
            job = _queue.enqueue(rq_tasks.refresh_previews, items)
            _preview_refresh_job_id = job.id
            _preview_refresh_running = True
            return {"started": True, "job_id": job.id}
        except Exception as e:
            return {"started": False, "reason": "queue_error", "detail": str(e)}
    if _stream_capture is None or not _stream_capture.available:
        return {"started": False, "reason": "capture_unavailable"}
    _preview_refresh_running = True
    asyncio.create_task(_run_full_preview_refresh())
    return {"started": True}


def _sync_preview_refresh_from_job() -> None:
    """Обновить _preview_refresh_running и _preview_refresh_done_at по статусу RQ job."""
    global _preview_refresh_running, _preview_refresh_done_at, _preview_refresh_job_id
    if not _preview_refresh_job_id or _queue is None:
        return
    try:
        from rq.job import Job
        import time
        job = Job.fetch(_preview_refresh_job_id, connection=_queue.connection)
        if job.is_finished or job.is_failed:
            _preview_refresh_running = False
            _preview_refresh_done_at = job.ended_at.timestamp() if job.ended_at else time.time()
            _preview_refresh_job_id = None
    except Exception:
        pass


@app.get("/api/channels/preview-refresh/status")
async def channels_preview_refresh_status():
    """Статус цикла обновления превью: running, done_at (ISO или null). При RQ — по статусу job."""
    from datetime import datetime, timezone
    _sync_preview_refresh_from_job()
    done_at = None
    if _preview_refresh_done_at is not None:
        done_at = datetime.fromtimestamp(_preview_refresh_done_at, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"running": _preview_refresh_running, "done_at": done_at}


@app.get("/api/channels/preview-refresh/stream")
async def channels_preview_refresh_stream():
    """
    SSE: уведомление о завершении цикла обновления превью.
    Событие refresh_done с done_at — подключайтесь при заходе на вкладку Каналы вместо опроса status.
    """
    from datetime import datetime, timezone

    async def event_stream():
        while True:
            _sync_preview_refresh_from_job()
            if not _preview_refresh_running and _preview_refresh_done_at is not None:
                done_at_iso = datetime.fromtimestamp(
                    _preview_refresh_done_at, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
                yield f"event: refresh_done\ndata: {{\"done_at\":\"{done_at_iso}\"}}\n\n"
                return
            yield ": keepalive\n\n"
            await asyncio.sleep(1.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- Скриншот и просмотр потоков (UDP/HTTP) ---
@app.get("/api/instances/{instance_id}/channels/preview")
async def channel_preview(instance_id: int, name: str):
    """
    Превью канала только из кэша (обновление — воркер по POST /api/channels/preview-refresh/start).
    Если файла нет в кэше — 404 (без захвата в запросе, чтобы не было 502).
    """
    from datetime import datetime, timezone

    data = await aggregated_channels()
    ch = next(
        (c for c in (data.get("channels") or []) if c.get("instance_id") == instance_id and c.get("name") == name),
        None,
    )
    if not ch:
        raise HTTPException(404, detail="Channel not found")
    if not (ch.get("output") or []):
        raise HTTPException(404, detail="Channel has no output URL")
    cache_path = _preview_cache_path(instance_id, name)
    if not cache_path.exists():
        raise HTTPException(404, detail="Preview not in cache yet")
    mtime = cache_path.stat().st_mtime
    headers = {"X-Preview-Generated-At": datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    return FileResponse(cache_path, media_type="image/jpeg", headers=headers)


@app.get("/api/instances/{instance_id}/channels/analyze")
async def channel_analyze(request: Request, instance_id: int, name: str):
    """Анализ потока канала через TSDuck (tsp): PAT/PMT, битрейт, сервисы."""
    try:
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
        pair = get_instance_by_id(instance_id)
        stream_host = pair[0].host if pair else None
        url = _normalize_stream_url(outputs[0], stream_host)
        analyzer = TsAnalyzer()
        per_ip = await _per_ip_semaphore("analyze", _client_ip(request), get_settings().heavy_analyze_per_ip)
        async with per_ip, _optional_sem(_HEAVY_ANALYZE_SEMAPHORE):
            ok, output = await asyncio.to_thread(analyzer.analyze, url, timeout_sec=8.0)
        return {"ok": ok, "output": output, "url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=str(e))


@app.post("/api/streams/playback")
async def start_stream_playback(request: Request, body: dict):
    """
    Запустить сессию просмотра. body: { "url": "udp://..." } или { "instance_id": int, "channel_name": str }.
    Возвращает playback_url для плеера (готовый http или /api/streams/{id}/playlist.m3u8).
    """
    try:
        url = body.get("url")
        stream_host = None
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
            pair = get_instance_by_id(instance_id)
            if pair:
                stream_host = pair[0].host
        url = _normalize_stream_url(url, stream_host)
        per_ip = await _per_ip_semaphore("playback", _client_ip(request), get_settings().heavy_playback_per_ip)
        async with per_ip, _optional_sem(_HEAVY_PLAYBACK_SEMAPHORE):
            session = StreamPlaybackSession()
            playback_url = session.start(url)
            sid = session._session_id
            if sid:
                _playback_sessions[sid] = session
            # Для HLS (FFmpeg) дождаться появления playlist.m3u8, иначе плеер получит 404
            playlist_path = session.get_playlist_path()
            if playlist_path is not None:
                for _ in range(30):
                    if await asyncio.to_thread(playlist_path.exists):
                        break
                    await asyncio.sleep(0.5)
                else:
                    err = "FFmpeg не создал плейлист (таймаут или ошибка входа)"
                    try:
                        be = session._backend_instance
                        if be is not None and getattr(be, "_process", None) is not None:
                            p = be._process
                            if p.stderr and p.poll() is not None:
                                err = (p.stderr.read() or b"").decode(errors="replace").strip()[:500] or err
                    except Exception:
                        pass
                    session.stop()
                    if sid:
                        _playback_sessions.pop(sid, None)
                    raise HTTPException(502, detail=err)
        # HLS по HTTP → native video (Safari и др.); сырой MPEG-TS по HTTP → mpegts.js (MSE) на фронте
        use_native_video = session.get_http_url() is not None and ".m3u8" in (url or "").lower()
        use_mpegts_js = (
            (session.get_http_url() is not None and ".m3u8" not in (url or "").lower())
            or session.get_udp_url() is not None
        )
        return {"playback_url": playback_url, "session_id": sid, "use_native_video": use_native_video, "use_mpegts_js": use_mpegts_js}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=str(e))


@app.get("/api/streams/live/{session_id}")
async def stream_live_udp(session_id: str, request: Request):
    """
    Стрим UDP-потока: сырой MPEG-TS по HTTP или HLS (редирект на playlist.m3u8).
    HLS: FFmpeg, VLC, GStreamer, TSDuck; Astra — только http_ts.
    """
    session = _playback_sessions.get(session_id)
    if not session:
        raise HTTPException(404, detail="Session not found")
    udp_url = session.get_udp_url()
    if not udp_url:
        raise HTTPException(404, detail="Not a UDP session")
    pref = get_stream_playback_udp_backend()
    opts = get_stream_playback_udp_backend_options()
    input_type = "udp_ts"
    out_pref = get_stream_playback_udp_output_format()
    desired_output = "http_hls" if out_pref == "hls" else "http_ts"
    chain = get_udp_to_http_backend_chain(pref)

    # HLS: первый бэкенд из цепочки с поддержкой http_hls и методом start_hls (FFmpeg, VLC, GStreamer, TSDuck)
    if desired_output == "http_hls":
        if session.get_session_dir() is not None:
            return RedirectResponse(
                url=f"/api/streams/{session_id}/playlist.m3u8",
                status_code=302,
                headers={"Cache-Control": "no-cache"},
            )
        session_dir = session._output_base / session_id
        process = None
        for name in chain:
            backend_cls = UDP_TO_HTTP_BACKENDS_BY_NAME.get(name)
            if (
                not backend_cls
                or "http_hls" not in getattr(backend_cls, "output_types", set())
                or not backend_cls.available(opts)
            ):
                continue
            start_hls_fn = getattr(backend_cls, "start_hls", None)
            if not callable(start_hls_fn):
                continue
            try:
                process = start_hls_fn(udp_url, session_dir, opts)
                break
            except Exception:
                continue
        if process is None:
            raise HTTPException(502, detail="Нет доступного бэкенда с поддержкой HLS (FFmpeg, VLC, GStreamer, TSDuck)")
        session.set_live_hls(session_dir, process)
        for _ in range(15):
            if (session_dir / "playlist.m3u8").exists():
                break
            await asyncio.sleep(0.2)
        return RedirectResponse(
            url=f"/api/streams/{session_id}/playlist.m3u8",
            status_code=302,
            headers={"Cache-Control": "no-cache"},
        )

    for name in chain:
        backend_cls = UDP_TO_HTTP_BACKENDS_BY_NAME.get(name)
        if (
            not backend_cls
            or input_type not in getattr(backend_cls, "input_types", set())
            or desired_output not in getattr(backend_cls, "output_types", set())
            or not backend_cls.available(opts)
        ):
            continue
        try:
            return StreamingResponse(
                backend_cls.stream(udp_url, request, opts),
                media_type="video/mp2t" if desired_output == "http_ts" else "application/vnd.apple.mpegurl",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        except NotImplementedError:
            continue
    if pref != "auto" and pref in UDP_TO_HTTP_BACKENDS_BY_NAME:
        raise HTTPException(502, detail=f"Бэкенд «{pref}» выбран, но недоступен или не реализован")
    raise HTTPException(502, detail="Нет доступного бэкенда для UDP")


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
    try:
        if not file_path.resolve().is_relative_to(session_dir.resolve()):
            raise HTTPException(403, detail="Invalid path")
    except ValueError:
        raise HTTPException(403, detail="Invalid path")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, detail=f"File not found: {path} (session alive: {session.is_alive()})")
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


@app.get("/api/settings")
async def get_settings_api():
    """
    Настройки WebUI по модулям. modules.stream — потоки (превью, воспроизведение UDP).
    """
    settings = get_webui_settings()
    capture_opts = get_stream_capture_backend_options()
    return {
        "modules": settings["modules"],
        "available": {
            "capture": get_available_capture_backends(capture_opts),
            # Для UI считаем доступность UDP-бэкендов под тип входа udp_ts и вывод http_ts.
            "playback_udp": get_available_udp_to_http_backends(
                get_stream_playback_udp_backend_options(),
                input_type="udp_ts",
                output_type="http_ts",
            ),
        },
        "current_capture_backend": _stream_capture.backend_name if (_stream_capture and _stream_capture.available) else None,
    }


@app.put("/api/settings")
async def put_settings_api(body: SettingsPutBody):
    """Сохранить настройки WebUI. body.modules — вложенная структура по модулям (мержится с текущей)."""
    global _stream_capture
    if body.modules is not None:
        save_webui_settings({"modules": body.modules})
    _stream_capture = _create_stream_capture_from_settings()
    settings = get_webui_settings()
    capture_opts = get_stream_capture_backend_options()
    return {
        "modules": settings["modules"],
        "available": {
            "capture": get_available_capture_backends(capture_opts),
            "playback_udp": get_available_udp_to_http_backends(
                get_stream_playback_udp_backend_options(),
                input_type="udp_ts",
                output_type="http_ts",
            ),
        },
        "current_capture_backend": _stream_capture.backend_name if (_stream_capture and _stream_capture.available) else None,
    }


@app.get("/api/streams/proxy/{session_id}/{path:path}")
async def stream_proxy(session_id: str, path: str):
    """Проксирование HTTP-потока через бэкенд (обход CORS). Для живого MPEG-TS — стриминг."""
    session = _playback_sessions.get(session_id)
    if not session:
        raise HTTPException(404, detail="Session not found")
    base = session.get_http_base_url()
    if not base:
        raise HTTPException(404, detail="Not an HTTP session")
    import httpx
    if path:
        url = base + path
    else:
        url = session.get_http_url()
    if not url:
        raise HTTPException(404, detail="No URL")
    is_live_ts = not path and not url.rstrip("/").lower().endswith(".m3u8")
    media_type = "application/vnd.apple.mpegurl" if (path.endswith(".m3u8") or (not path and ".m3u8" in url.lower())) else "video/mp2t"
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            if is_live_ts:
                async with client.stream("GET", url) as r:
                    r.raise_for_status()
                    async def chunk_gen():
                        async for chunk in r.aiter_bytes():
                            yield chunk
                    return StreamingResponse(chunk_gen(), media_type=media_type)
            r = await client.get(url)
            r.raise_for_status()
            return Response(content=r.content, media_type=media_type)
    except Exception as e:
        raise HTTPException(502, detail=str(e))


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
        raise HTTPException(502, detail=data.get("_error", "Unreachable") if isinstance(data, dict) else "Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=data if isinstance(data, dict) else "Upstream error")
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


def _proxy_detail(data, default: str = "Upstream error or invalid response"):
    """Безопасный detail для HTTPException при прокси: Astra мог вернуть не-JSON."""
    if data is None:
        return default
    if isinstance(data, dict):
        return data
    return str(data)[:500]


@app.get("/api/instances/{instance_id}/system/network/interfaces")
async def proxy_system_network_interfaces(instance_id: int):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_system_network_interfaces()
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable") if isinstance(data, dict) else "Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=_proxy_detail(data))
    return data if isinstance(data, dict) else {}


@app.get("/api/instances/{instance_id}/system/network/hostname")
async def proxy_system_network_hostname(instance_id: int):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_system_network_hostname()
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable") if isinstance(data, dict) else "Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=_proxy_detail(data))
    return data if isinstance(data, dict) else {}


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
        raise HTTPException(502, detail=data.get("_error", "Unreachable") if isinstance(data, dict) else "Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=_proxy_detail(data))
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
        raise HTTPException(502, detail=data.get("_error", "Unreachable") if isinstance(data, dict) else "Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=_proxy_detail(data))
    return data or {"message": "exit scheduled"}


@app.post("/api/instances/{instance_id}/system/clear-cache")
async def proxy_system_clear_cache(instance_id: int):
    """Очистка кэша системных метрик Astra."""
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.system_clear_cache()
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable") if isinstance(data, dict) else "Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=_proxy_detail(data))
    return data or {"message": "Metrics updated"}


@app.get("/api/instances/{instance_id}/utils/info")
async def proxy_utils_info(instance_id: int):
    c = _client(instance_id)
    if not c:
        raise HTTPException(404, "Instance not found")
    code, data = await c.get_utils_info()
    if code == 0:
        raise HTTPException(502, detail=data.get("_error", "Unreachable") if isinstance(data, dict) else "Unreachable")
    if code >= 400:
        raise HTTPException(code, detail=_proxy_detail(data))
    return data if isinstance(data, dict) else {}
