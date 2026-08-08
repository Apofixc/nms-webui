"""Единая модель пагинации для API NMS-WebUI."""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Стандартный формат ответа с пагинацией."""
    items: list[T] = Field(description="Список элементов текущей страницы")
    total: int = Field(description="Общее количество элементов в БД")
    limit: int = Field(description="Запрошенное количество элементов на страницу")
    offset: int = Field(description="Смещение от начала списка")
