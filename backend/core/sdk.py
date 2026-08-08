"""Module SDK — единая точка входа для разработки модулей и виджетов.

Собирает в одном месте всё публичное API платформы, которое нужно
разработчику модуля: контекст, базовые классы, схемы виджетов,
DI-хелперы, исключения, доступы (RBAC), i18n, события и уведомления.

Использование в модуле:

    from backend.core.sdk import (
        BaseModule,
        ModuleContext,
        WidgetDataResponse,
        WidgetMetric,
        WidgetStatus,
        require_permission,
        CurrentUser,
        NotFoundError,
        tr,
    )
"""
from __future__ import annotations

# --- Контекст и базовые классы модулей ---
from backend.core.auth import CurrentUser, require_permission
from backend.core.database import get_system_setting, set_system_setting
from backend.core.events import broadcaster, notify_settings_changed

# --- Исключения ---
from backend.core.exceptions import (
    AuthenticationError,
    ModuleDisabledError,
    NMSError,
    NMSModuleNotFoundError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitExceededError,
    ValidationError,
    register_exception,
)

# --- Локализация ---
from backend.core.i18n import register_module_messages, tr

# --- Логи модулей ---
from backend.core.log_providers import (
    BaseLogProvider,
    LocalFileLogProvider,
    RemoteHTTPLogProvider,
    log_provider_registry,
)

# --- Уведомления ---
from backend.core.notifications_api import create_notification
from backend.core.plugin.context import ModuleContext

# --- FastAPI DI-хелперы ---
from backend.core.plugin.dependencies import get_module_context, get_module_instance

# --- Реестр модулей ---
from backend.core.plugin.registry import (
    get_instance,
    get_manifest,
    get_module_settings,
    is_module_active,
    is_module_enabled,
    save_module_settings,
)

# --- Схемы виджетов ---
from backend.core.plugin.widgets import (
    WidgetAction,
    WidgetDataResponse,
    WidgetMetric,
    WidgetStatus,
    WidgetType,
)
from backend.modules.base import BaseModule, BaseSubmodule, ModuleStatusResponse

__all__ = [
    "AuthenticationError",
    # Логи
    "BaseLogProvider",
    "BaseModule",
    "BaseSubmodule",
    # RBAC
    "CurrentUser",
    "LocalFileLogProvider",
    # Контекст и базовые классы
    "ModuleContext",
    "ModuleDisabledError",
    "ModuleStatusResponse",
    # Исключения
    "NMSError",
    "NMSModuleNotFoundError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitExceededError",
    "RemoteHTTPLogProvider",
    "ValidationError",
    "WidgetAction",
    "WidgetDataResponse",
    "WidgetMetric",
    # Виджеты
    "WidgetStatus",
    "WidgetType",
    # События и уведомления
    "broadcaster",
    "create_notification",
    # Реестр
    "get_instance",
    "get_manifest",
    "get_module_context",
    # DI-хелперы
    "get_module_instance",
    "get_module_settings",
    # Системные настройки
    "get_system_setting",
    "is_module_active",
    "is_module_enabled",
    "log_provider_registry",
    "notify_settings_changed",
    "register_exception",
    "register_module_messages",
    "require_permission",
    "save_module_settings",
    "set_system_setting",
    # Локализация
    "tr",
]
