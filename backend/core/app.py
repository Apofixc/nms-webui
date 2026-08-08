"""create_app() — фабрика FastAPI-приложения."""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.core.database import get_db_connection, init_db
from backend.core.events import router as events_router
from backend.core.exceptions import register_exception_handlers
from backend.core.logger import setup_logging
from backend.core.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    LOADED_MODULES_COUNT,
    metrics_endpoint_handler,
)
from backend.core.notifications_api import router as notifications_router
from backend.core.plugin.api import router as modules_router
from backend.core.plugin.loader import load_all_modules
from backend.core.plugin.registry import get_all_instances, shutdown_all
from backend.core.system_api import router as system_router
from backend.core.users_api import router as users_router

_log = logging.getLogger("nms.app")


async def notifications_cleanup_loop():
    """Фоновая регулярная очистка устаревших прочитанных уведомлений (TTL 30 дней) раз в 24 часа."""
    import asyncio

    from backend.core.database import cleanup_old_notifications
    while True:
        try:
            cleaned = cleanup_old_notifications(days=30)
            if cleaned > 0:
                _log.info("Auto-cleaned %d old notifications", cleaned)
        except Exception as exc:
            _log.warning("Failed to auto-clean notifications: %s", exc)
        await asyncio.sleep(86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup / shutdown."""
    import asyncio
    # Инициализация SQLite БД и фалов
    init_db()
    from backend.core.log_providers import load_remote_sources_from_db
    load_remote_sources_from_db()

    # Запуск фонового таска автоочистки устаревших уведомлений
    cleanup_task = asyncio.create_task(notifications_cleanup_loop())

    # Запуск всех загруженных модулей при активном event loop
    instances = get_all_instances()
    LOADED_MODULES_COUNT.set(len(instances))
    for mid, inst in instances.items():
        if hasattr(inst, "start"):
            try:
                inst.start()
                _log.info("Module %s started successfully", mid)
            except Exception as exc:
                _log.error("Failed to start module %s: %s", mid, exc)

    yield
    # Корректная остановка фоновых задач и всех модулей
    cleanup_task.cancel()
    await shutdown_all()


def create_app() -> FastAPI:
    """Создать и настроить FastAPI-приложение."""
    setup_logging()

    app = FastAPI(
        title="NMS API",
        version="0.1.0",
        lifespan=lifespan,
    )

    from backend.core.config import get_settings
    settings = get_settings()

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID, Prometheus Metrics & Security Headers Middleware
    @app.middleware("http")
    async def request_context_and_metrics_middleware(request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        endpoint = request.url.path
        method = request.method
        status_code = str(response.status_code)

        # Регистрация метрик
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)

        # Заголовки ответа
        response.headers["X-Request-ID"] = req_id
        if settings.secure_headers_enabled:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    # Exception handlers
    register_exception_handlers(app)

    # Prometheus metrics endpoint
    app.add_route("/metrics", metrics_endpoint_handler)

    # Core routers: /api/v1 (версионированные эндпоинты)
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(system_router, prefix="/api/v1")
    app.include_router(modules_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")

    # Legacy routers: /api (алиасы обратной совместимости)
    app.include_router(users_router)
    app.include_router(system_router)
    app.include_router(modules_router)
    app.include_router(events_router)
    app.include_router(notifications_router)

    # Discover & load plugin modules
    load_all_modules(app)

    # Root health-check & Probes
    @app.get("/")
    async def root():
        return {"service": "NMS API", "docs": "/docs", "version": "v1"}

    @app.get("/health/live")
    async def liveness_probe():
        return {"status": "alive"}

    @app.get("/health/ready")
    async def readiness_probe():
        try:
            conn = get_db_connection()
            conn.execute("SELECT 1").fetchone()
            conn.close()
            return {"status": "ready", "database": "connected"}
        except Exception as exc:
            return Response(
                content=f'{{"status": "not_ready", "error": "{exc}"}}',
                status_code=503,
                media_type="application/json",
            )

    @app.get("/health")
    @app.get("/api/health")
    @app.get("/api/v1/health")
    async def health_check():
        from backend.core.system_api import get_system_health
        return await get_system_health()

    return app
