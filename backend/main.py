"""NMS API: прокси и агрегация lib-monitor (Astra)."""
from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import load_instances
from backend.core.module_router import load_module_routers
from backend.modules.astra.services.health_checker import run_loop as health_checker_run


_log = logging.getLogger("nms.stream")

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

_health_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _health_task
    load_instances()
    _health_task = asyncio.create_task(health_checker_run())
    yield
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
