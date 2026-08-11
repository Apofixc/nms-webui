"""Тесты SDK ModuleContext и разрешённого публичного API ядра."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.core.database import get_db_connection, get_system_setting, set_system_setting
from backend.core.plugin.context import ModuleContext, ModuleSettings
from backend.core.public import (
    AuthenticationError,
    BaseLogProvider,
    BaseModule,
    BaseSubmodule,
    CurrentUser,
    LocalFileLogProvider,
    ModuleContext as PublicModuleContext,
    ModuleDisabledError,
    ModuleStatusResponse,
    NMSError,
    PermissionDeniedError,
    RemoteHTTPLogProvider,
    ValidationError,
    create_access_token,
    decode_access_token,
    decrypt_secret,
    encrypt_secret,
    get_lang,
    mask_secret,
    require_permission,
    tr,
    user_has_permission,
)


@pytest.fixture
def dummy_context(tmp_path: Path) -> ModuleContext:
    return ModuleContext(
        module_id="test_dummy_module",
        root=tmp_path,
        manifest={"name": "Test Dummy Module"},
    )


def test_public_imports_export():
    """Проверка доступности экспортируемых символов публичного фасадного API."""
    assert PublicModuleContext is ModuleContext
    assert issubclass(AuthenticationError, NMSError)
    assert issubclass(PermissionDeniedError, NMSError)
    assert issubclass(ValidationError, NMSError)
    assert issubclass(ModuleDisabledError, NMSError)
    assert callable(require_permission)
    assert callable(tr)
    assert callable(get_lang)
    assert callable(encrypt_secret)
    assert callable(decrypt_secret)
    assert callable(mask_secret)
    assert issubclass(LocalFileLogProvider, BaseLogProvider)
    assert issubclass(RemoteHTTPLogProvider, BaseLogProvider)
    assert callable(user_has_permission)
    assert callable(create_access_token)
    assert callable(decode_access_token)


def test_ctx_settings_get_and_set(dummy_context: ModuleContext):
    """Проверка работы ctx.settings.get() и ctx.settings.set()."""
    # 1. Запись единичного ключа
    dummy_context.settings.set("interval", 42)
    assert dummy_context.settings.get("interval") == 42
    assert dummy_context.settings.get("non_existent", default="def") == "def"

    # 2. Получение полного словаря настроек
    all_sett = dummy_context.settings.get()
    assert isinstance(all_sett, dict)
    assert all_sett.get("interval") == 42

    # 3. Пакетная запись словаря
    dummy_context.settings.set({"enabled": True, "hostname": "127.0.0.1"})
    assert dummy_context.settings.get("enabled") is True
    assert dummy_context.settings.get("hostname") == "127.0.0.1"
    assert dummy_context.settings.get("interval") == 42


def test_ctx_broadcast(dummy_context: ModuleContext):
    """Проверка отправки сообщений через ctx.broadcast()."""
    with patch("backend.core.events.broadcaster.broadcast") as mock_broadcast:
        # Отправка словаря
        payload_dict = {"type": "unit_test_event", "value": 100}
        dummy_context.broadcast(payload_dict)
        mock_broadcast.assert_called_once_with(data_dict=payload_dict, target_user_id=None)

        mock_broadcast.reset_mock()

        # Отправка строки для конкретного пользователя
        dummy_context.broadcast('{"type": "user_msg"}', target_user_id="usr_123")
        mock_broadcast.assert_called_once_with(message='{"type": "user_msg"}', target_user_id="usr_123")


def test_ctx_audit(dummy_context: ModuleContext):
    """Проверка записи событий аудита через ctx.audit()."""
    action_name = "test_module_action"
    details_data = {"key": "value", "status": "ok"}

    dummy_context.audit(
        action=action_name,
        details=details_data,
        user_id="usr_test_1",
        username="tester",
        ip_address="10.0.0.1",
    )

    # Проверяем запись в таблице audit_logs
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM audit_logs WHERE action = ? ORDER BY id DESC LIMIT 1",
            (action_name,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row["user_id"] == "usr_test_1"
        assert row["username"] == "tester"
        assert row["resource"] == f"module:{dummy_context.module_id}"
        assert row["ip_address"] == "10.0.0.1"
        assert json.loads(row["details"]) == details_data
    finally:
        conn.close()


def test_ctx_register_log_provider(dummy_context: ModuleContext):
    """Проверка регистрации log provider через ctx.register_log_provider()."""
    mock_provider = MagicMock()
    mock_provider.id = "test_custom_provider_id"

    with patch("backend.core.log_providers.log_provider_registry.register") as mock_reg:
        dummy_context.register_log_provider(mock_provider)
        mock_reg.assert_called_once_with(mock_provider)
