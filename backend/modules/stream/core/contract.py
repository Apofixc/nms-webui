from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.modules.stream.core.types import StreamResult, StreamTask


class IStreamBackend(ABC):
    """Контракт для всех stream-backend субмодулей."""

    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        """Вернуть словарь возможностей (обычно содержимое manifest.yaml)."""

    @abstractmethod
    def match_score(self, input_proto: str, output_format: str) -> int:
        """Вернуть 0-100: 0 — не поддерживается."""

    # Жизненный цикл
    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> bool:
        """Проверка зависимостей и подготовка ресурсов."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Проверка доступности бэкенда."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Освобождение ресурсов."""

    # Работа
    @abstractmethod
    async def process(self, task: StreamTask) -> StreamResult:
        """Выполнить задачу и вернуть результат."""
