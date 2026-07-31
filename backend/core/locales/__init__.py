"""Сборка сообщений локализации бэкенда из отдельных языковых файлов."""
from __future__ import annotations

from backend.core.locales.en import MESSAGES as EN_MESSAGES
from backend.core.locales.ru import MESSAGES as RU_MESSAGES


def _build_messages() -> dict[str, dict[str, str]]:
    all_keys = set(RU_MESSAGES.keys()) | set(EN_MESSAGES.keys())
    result: dict[str, dict[str, str]] = {}
    for key in all_keys:
        result[key] = {}
        if key in RU_MESSAGES:
            result[key]["ru"] = RU_MESSAGES[key]
        if key in EN_MESSAGES:
            result[key]["en"] = EN_MESSAGES[key]
    return result


BACKEND_MESSAGES: dict[str, dict[str, str]] = _build_messages()

__all__ = ["BACKEND_MESSAGES"]
