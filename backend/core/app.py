"""create_app() — фабрика FastAPI-приложения."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import load_instances
from backend.core.exceptions import register_exception_handlers
from backend.core.logger import setup_logging
from backend.core.plugin.api import router as modules_router
from backend.core.events import router as events_router
from backend.core.plugin.loader import load_all_modules
from backend.core.plugin.registry import shutdown_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup / shutdown."""
    load_instances()
    yield
    # Корректная остановка всех модулей
    shutdown_all()


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
    app.include_router(modules_router)
    app.include_router(events_router)

    # Discover & load plugin modules
    load_all_modules(app)

    # Root health-check
    @app.get("/")
    async def root():
        return {"service": "NMS API", "docs": "/docs"}

    return app
