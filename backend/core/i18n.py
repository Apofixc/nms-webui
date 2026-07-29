"""Backend i18n helper utilities."""
from __future__ import annotations

from typing import Optional
from fastapi import Request


def get_lang(request: Optional[Request]) -> str:
    """Извлечь язык из заголовков HTTP запроса."""
    if not request:
        return "ru"
    accept = request.headers.get("accept-language", "")
    if "en" in accept.lower():
        return "en"
    return "ru"


def tr(request: Optional[Request], ru: str, en: str) -> str:
    """Вернуть ru или en строку на основе языка запроса."""
    return en if get_lang(request) == "en" else ru
