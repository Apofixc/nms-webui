"""Глобальные ошибки и exception handlers для FastAPI."""
from __future__ import annotations

import logging
from typing import Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

_log = logging.getLogger("nms.exceptions")


class NMSError(Exception):
    """Базовое единое исключение для NMS-WebUI."""

    def __init__(
        self,
        message: str = "Internal error",
        status_code: int = 400,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}
        super().__init__(message)


class NMSModuleNotFoundError(NMSError):
    """Модуль не найден."""

    def __init__(self, module_id: str):
        super().__init__(
            message=f"Module '{module_id}' not found",
            status_code=404,
            code="MODULE_NOT_FOUND",
            details={"module_id": module_id},
        )


class ModuleDisabledError(NMSError):
    """Модуль отключён."""

    def __init__(self, module_id: str):
        super().__init__(
            message=f"Module '{module_id}' is disabled",
            status_code=403,
            code="MODULE_DISABLED",
            details={"module_id": module_id},
        )


def register_exception(
    app: FastAPI,
    exc_class: type[Exception],
    code: str = "CUSTOM_ERROR",
    status_code: int = 400,
) -> None:
    """Зарегистрировать кастомное исключение с единым JSON-шаблоном ответа."""

    @app.exception_handler(exc_class)
    async def _handler(_request: Request, exc: Exception) -> JSONResponse:
        message = getattr(exc, "message", str(exc))
        details = getattr(exc, "details", {})
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "details": details,
                }
            },
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрация глобальных обработчиков исключений."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            code = exc.detail.get("error_code", "HTTP_ERROR")
            message = str(exc.detail.get("detail", exc.detail))
            details = exc.detail.get("params", {})
        else:
            code = "HTTP_ERROR"
            message = str(exc.detail)
            details = {}

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "details": details,
                }
            },
            headers=exc.headers,
        )

    @app.exception_handler(NMSError)
    async def nms_error_handler(_request: Request, exc: NMSError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        _log.exception("Unhandled server exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Internal server error",
                    "details": {},
                }
            },
        )



