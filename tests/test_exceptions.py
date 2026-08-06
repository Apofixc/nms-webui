"""Тесты для модуля backend/core/exceptions.py"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.core.exceptions import (
    NMSError,
    NMSModuleNotFoundError,
    ModuleDisabledError,
    register_exception_handlers,
)


def test_nms_exceptions_instantiation():
    """Проверка создания объектов исключений."""
    err = NMSError("Custom error", 400)
    assert err.message == "Custom error"
    assert err.status_code == 400

    not_found = NMSModuleNotFoundError("test_mod")
    assert not_found.status_code == 404
    assert "test_mod" in not_found.message

    disabled = ModuleDisabledError("test_mod")
    assert disabled.status_code == 403
    assert "disabled" in disabled.message


def test_exception_handlers_http_exception():
    """Проверка перехвата HTTPException."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/string-error")
    def string_error():
        raise HTTPException(status_code=400, detail="Bad input")

    @app.get("/dict-error")
    def dict_error():
        raise HTTPException(status_code=422, detail={"error_code": "INVALID_PARAM", "field": "name"})

    client = TestClient(app)

    res1 = client.get("/string-error")
    assert res1.status_code == 400
    assert res1.json() == {"detail": "Bad input", "error": "Bad input"}

    res2 = client.get("/dict-error")
    assert res2.status_code == 422
    assert res2.json() == {"error_code": "INVALID_PARAM", "field": "name"}


def test_exception_handlers_nms_error():
    """Проверка перехвата NMSError и дочерних ошибок."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/nms-error")
    def nms_err():
        raise NMSModuleNotFoundError("tuya")

    client = TestClient(app)

    res = client.get("/nms-error")
    assert res.status_code == 404
    assert res.json() == {
        "error": "Module 'tuya' not found",
        "detail": "Module 'tuya' not found",
    }


def test_exception_handlers_generic_exception():
    """Проверка скрытия чувствительных данных при 500 ошибках."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/unhandled-error")
    def unhandled():
        raise RuntimeError("Sensitive DB password: super_secret_123")

    client = TestClient(app, raise_server_exceptions=False)

    res = client.get("/unhandled-error")
    assert res.status_code == 500
    data = res.json()
    assert data == {"error": "Internal server error", "detail": "Internal server error"}
    assert "super_secret_123" not in str(data)
