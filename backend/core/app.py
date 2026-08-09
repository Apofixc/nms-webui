"""create_app() — фабрика FastAPI-приложения."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import api_router
from backend.core.database import init_db
from backend.core.exceptions import register_exception_handlers
from backend.core.logger import setup_logging
from backend.core.plugin.loader import load_all_modules
from backend.core.plugin.registry import shutdown_all, get_all_instances

from backend.core.auth import get_allowed_cors_origins
from backend.core.events import ws_manager
from backend.core.log_providers import shared_log_stream_manager

_log = logging.getLogger("nms.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup / shutdown."""
    import asyncio
    # Инициализация SQLite БД
    init_db()
    from backend.core.events import bus_ws_bridge
    bus_ws_bridge.setup()
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
    # Корректное закрытие всех открытых WebSocket соединений (Graceful Shutdown)
    try:
        await ws_manager.close_all(code=1001, reason="Server shutting down")
        await shared_log_stream_manager.close_all(code=1001, reason="Server shutting down")
    except Exception as exc:
        _log.warning("Error during WS graceful shutdown: %s", exc)

    # Корректная остановка всех модулей
    await shutdown_all()

    # Остановка шины событий и завершение фоновых задач
    from backend.core.bus import event_bus
    await event_bus.shutdown()



def create_app() -> FastAPI:
    """Создать и настроить FastAPI-приложение."""
    setup_logging()

    app = FastAPI(
        title="NMS API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS настройка с использованием безопасного списка разрешенных origin
    allowed_origins = get_allowed_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True if "*" not in allowed_origins else False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    # Exception handlers
    register_exception_handlers(app)

    # Подключение всех API маршрутов
    app.include_router(api_router)

    # Discover & load plugin modules
    load_all_modules(app)

    # Root health-check
    @app.get("/")
    async def root():
        return {"service": "NMS API", "docs": "/docs"}

    @app.get("/health")
    @app.get("/api/health")
    async def health_check():
        from backend.api.system import get_system_health
        return await get_system_health()

    return app
