"""create_app() — фабрика FastAPI-приложения."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.database import init_db
from backend.core.events import router as events_router
from backend.core.exceptions import register_exception_handlers
from backend.core.logger import setup_logging
from backend.core.plugin.api import router as modules_router
from backend.core.plugin.loader import load_all_modules
from backend.core.plugin.registry import shutdown_all, get_all_instances
from backend.core.system_api import router as system_router
from backend.core.users_api import router as users_router

_log = logging.getLogger("nms.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup / shutdown."""
    # ИнициализацияSQLite БД
    init_db()
    from backend.core.log_providers import load_remote_sources_from_db
    load_remote_sources_from_db()
    
    # Запуск всех загруженных модулей при активном event loop
    for mid, inst in get_all_instances().items():
        if hasattr(inst, "start"):
            try:
                inst.start()
                _log.info("Module %s started successfully", mid)
            except Exception as exc:
                _log.error("Failed to start module %s: %s", mid, exc)
                
    yield
    # Корректная остановка всех модулей
    await shutdown_all()


def create_app() -> FastAPI:
    """Создать и настроить FastAPI-приложение."""
    setup_logging()

    app = FastAPI(
        title="NMS API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    register_exception_handlers(app)

    # System module endpoints
    app.include_router(users_router)
    app.include_router(system_router)
    app.include_router(modules_router)
    app.include_router(events_router)

    # Discover & load plugin modules
    load_all_modules(app)

    # Root health-check
    @app.get("/")
    async def root():
        return {"service": "NMS API", "docs": "/docs"}

    @app.get("/health")
    @app.get("/api/health")
    async def health_check():
        from backend.core.system_api import get_system_health
        return await get_system_health()

    return app
