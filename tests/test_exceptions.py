"""Тесты для модуля backend/core/exceptions.py"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.core.exceptions import (
    NMSError,
    NMSModuleNotFoundError,
    ModuleDisabledError,
    register_exception,
    register_exception_handlers,
)


def test_nms_exceptions_instantiation():
    """Проверка создания объектов исключений."""
    err = NMSError("Custom error", status_code=400, code="CUSTOM_ERR", details={"foo": "bar"})
    assert err.message == "Custom error"
    assert err.status_code == 400
    assert err.code == "CUSTOM_ERR"
    assert err.details == {"foo": "bar"}

    not_found = NMSModuleNotFoundError("test_mod")
    assert not_found.status_code == 404
    assert not_found.code == "MODULE_NOT_FOUND"
    assert not_found.details == {"module_id": "test_mod"}

    disabled = ModuleDisabledError("test_mod")
    assert disabled.status_code == 403
    assert disabled.code == "MODULE_DISABLED"
    assert disabled.details == {"module_id": "test_mod"}


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
    assert res1.json() == {
        "error": {
            "code": "HTTP_ERROR",
            "message": "Bad input",
            "details": {},
        }
    }

    res2 = client.get("/dict-error")
    assert res2.status_code == 422
    assert res2.json() == {
        "error": {
            "code": "INVALID_PARAM",
            "message": "{'error_code': 'INVALID_PARAM', 'field': 'name'}",
            "details": {},
        }
    }


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
        "error": {
            "code": "MODULE_NOT_FOUND",
            "message": "Module 'tuya' not found",
            "details": {"module_id": "tuya"},
        }
    }


def test_register_custom_exception():
    """Проверка регистрации произвольного класса исключения."""

    class ExternalLibError(Exception):
        pass

    app = FastAPI()
    register_exception_handlers(app)
    register_exception(app, ExternalLibError, code="EXTERNAL_SDK_FAIL", status_code=502)

    @app.get("/external-error")
    def ext_err():
        raise ExternalLibError("SDK network timeout")

    client = TestClient(app)

    res = client.get("/external-error")
    assert res.status_code == 502
    assert res.json() == {
        "error": {
            "code": "EXTERNAL_SDK_FAIL",
            "message": "SDK network timeout",
            "details": {},
        }
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
    assert data == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
            "details": {},
        }
    }
    assert "super_secret_123" not in str(data)

