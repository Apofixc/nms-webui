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
    def stop(self) -> None:
        """Остановка модуля и освобождение ресурсов."""

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Возврат текущего состояния модуля."""


class BaseSubmodule(BaseModule, ABC):
    """Контракт подмодуля с привязкой к родительскому модулю."""

    @property
    def parent_module_id(self) -> str | None:
        return self.context.parent_module_id
