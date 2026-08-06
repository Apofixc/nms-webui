"""Глобальные ошибки и exception handlers для FastAPI."""
from __future__ import annotations

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

_log = logging.getLogger("nms.exceptions")


class NMSError(Exception):
    """Базовое исключение для NMS-WebUI."""

    def __init__(self, message: str = "Internal error", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NMSModuleNotFoundError(NMSError):
    """Модуль не найден."""

    def __init__(self, module_id: str):
        super().__init__(f"Module '{module_id}' not found", status_code=404)


class ModuleDisabledError(NMSError):
    """Модуль отключён."""

    def __init__(self, module_id: str):
        super().__init__(f"Module '{module_id}' is disabled", status_code=403)


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрация глобальных обработчиков исключений."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            content = dict(exc.detail)
        else:
            content = {"detail": exc.detail}
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=exc.headers,
        )

    @app.exception_handler(NMSError)
    async def nms_error_handler(_request: Request, exc: NMSError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        _log.exception("Unhandled server exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


