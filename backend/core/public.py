"""Публичный интерфейс ядра (Public Core SDK API).

Разрешённые прямые импорты для модулей платформы.
Все сущности, требующие module_id, должны взаимодействовать с ядром через ModuleContext.
"""
from __future__ import annotations

from backend.core.auth import (
    CurrentUser,
    create_access_token,
    decode_access_token,
    require_module_permission,
    require_permission,
    user_has_permission,
)
from backend.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from backend.core.exceptions import (
    AuthenticationError,
    ModuleDisabledError,
    ModuleValidationError,
    NMSError,
    NMSModuleNotFoundError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from backend.core.i18n import get_lang, tr
from backend.core.log_providers import BaseLogProvider, LocalFileLogProvider, RemoteHTTPLogProvider
from backend.core.plugin.context import ModuleContext
from backend.modules.base import BaseModule, BaseSubmodule, ModuleStatusResponse

__all__ = [
    # Модульные контракты и контекст
    "BaseModule",
    "BaseSubmodule",
    "ModuleStatusResponse",
    "ModuleContext",
    # Аутентификация и авторизация
    "CurrentUser",
    "require_permission",
    "require_module_permission",
    "user_has_permission",
    "create_access_token",
    "decode_access_token",
    # Локализация (i18n)
    "tr",
    "get_lang",
    # Криптография и секреты
    "encrypt_secret",
    "decrypt_secret",
    "mask_secret",
    # Базовые классы логов
    "BaseLogProvider",
    "LocalFileLogProvider",
    "RemoteHTTPLogProvider",
    # Ошибки
    "NMSError",
    "NMSModuleNotFoundError",
    "ModuleDisabledError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ValidationError",
    "ModuleValidationError",
]
