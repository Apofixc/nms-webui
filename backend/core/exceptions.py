"""Глобальные ошибки и exception handlers для FastAPI."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NMSError(Exception):
    """Base exception for NMS-WebUI."""

    def __init__(self, message: str = "Internal error", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ModuleNotFoundError(NMSError):
    """Module not found."""

    def __init__(self, module_id: str):
        super().__init__(f"Module '{module_id}' not found", status_code=404)


class ModuleDisabledError(NMSError):
    """Module is disabled."""

    def __init__(self, module_id: str):
        super().__init__(f"Module '{module_id}' is disabled", status_code=403)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(NMSError)
    async def nms_error_handler(_request: Request, exc: NMSError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc) or "Internal server error"},
        )
