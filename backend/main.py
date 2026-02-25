"""NMS API: прокси и агрегация lib-monitor (Astra)."""
from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import load_instances, get_settings
from backend.core.module_router import load_module_routers
from backend.modules.astra.services.health_checker import run_loop as health_checker_run
from backend.modules.stream.outputs.webrtc_output import whep_close
from backend.modules.stream.services.state import (
    create_stream_capture_from_settings,
    get_playback_sessions,
    get_whep_connections,
    init_heavy_semaphores,
    set_queue,
    set_stream_capture,
)


_log = logging.getLogger("nms.stream")

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

_health_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _health_task
    load_instances()
    init_heavy_semaphores()
    set_stream_capture(create_stream_capture_from_settings())
    _health_task = asyncio.create_task(health_checker_run())
    redis_url = get_settings().redis_url
    if redis_url:
        try:
            import redis
            from rq import Queue

            set_queue(Queue(connection=redis.Redis.from_url(redis_url), name="nms", default_timeout=3600))
        except Exception:
            set_queue(None)
    yield
    for sess in get_playback_sessions().values():
        sess.stop()
    get_playback_sessions().clear()
    for sid in list(get_whep_connections()):
        conn = get_whep_connections().pop(sid, None)
        if conn is not None:
            pc, player = conn if isinstance(conn, tuple) and len(conn) >= 2 else (conn, None)
            await whep_close(pc, player)
    if _health_task and not _health_task.done():
        _health_task.cancel()
        try:
            await _health_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="NMS API — lib-monitor", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

load_module_routers(app)


@app.get("/")
async def root():
    return {"service": "NMS API", "docs": "/docs"}
