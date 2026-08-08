"""Стандартизированные Pydantic-схемы для единого механизма виджетов."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WidgetStatus(str, Enum):
    """Статус состояния виджета или метрики."""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class WidgetType(str, Enum):
    """Тип визуального отображения виджета."""
    SUMMARY = "summary"
    STAT = "stat"
    LIST = "list"
    CUSTOM = "custom"


class WidgetMetric(BaseModel):
    """Отдельная метрика или счетчик виджета."""
    id: str
    label: str
    value: Any
    unit: str | None = None
    status: WidgetStatus = WidgetStatus.INFO
    icon: str | None = None


class WidgetAction(BaseModel):
    """Быстрое действие или ссылка на интерфейс модуля."""
    label: str
    path: str
    icon: str | None = None


class WidgetDataResponse(BaseModel):
    """Единый формат ответа для всех эндпоинтов виджетов."""
    status: WidgetStatus = WidgetStatus.OK
    type: WidgetType = WidgetType.SUMMARY
    title: str | None = None
    metrics: list[WidgetMetric] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[WidgetAction] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    extra: dict[str, Any] = Field(default_factory=dict)
