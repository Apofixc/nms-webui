"""Базовые абстракции для модулей и подмодулей."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.core.plugin.context import ModuleContext


class BaseModule(ABC):
    """Базовый контракт для модулей верхнего уровня."""

    def __init__(self, context: ModuleContext):
        self.context = context

    @abstractmethod
    def init(self) -> None:
        """Подготовка модуля (регистрация ресурсов, валидация конфигурации)."""

    @abstractmethod
    def start(self) -> None:
        """Запуск модуля и его сервисов."""

    @abstractmethod
    async def stop(self) -> None:
        """Остановка модуля и освобождение ресурсов."""

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Возврат текущего состояния модуля."""

    def get_log_provider(self) -> Any | None:
        """Опциональный провайдер логов модуля (если модуль ведет собственный лог)."""
        return None

    def uninstall(self) -> None:
        """Пользовательский деструктор при полном удалении модуля.

        Может быть переопределен модулем для дополнительной очистки ресурсов.
        Таблицы модуля mod_<module_id>_*, разрешительные права, настройки и уведомления
        очищаются ядром платформы автоматически.
        """
        pass


    def is_dependency_active(self, module_id: str) -> bool:
        """Проверить, активна ли обязательная или необязательная зависимость."""
        return self.context.is_module_active(module_id)

    def get_dependency_instance(self, module_id: str) -> Any | None:
        """Получить экземпляр зависимости (если она загружена и активна)."""
        return self.context.get_module_instance(module_id)


class BaseSubmodule(BaseModule, ABC):
    """Контракт подмодуля с привязкой к родительскому модулю."""

    @property
    def parent_module_id(self) -> str | None:
        return self.context.parent_module_id
