"""Backend i18n helper utilities."""
from __future__ import annotations

from typing import Optional
from fastapi import Request


def get_lang(request: Optional[Request]) -> str:
    """Извлечь язык из заголовков HTTP запроса. По умолчанию 'en'."""
    if not request:
        return "en"
    accept = request.headers.get("accept-language", "")
    if "ru" in accept.lower():
        return "ru"
    return "en"


def tr(request: Optional[Request], ru: str, en: str) -> str:
    """Вернуть ru или en строку на основе языка запроса."""
    return ru if get_lang(request) == "ru" else en


def make_error_detail(request: Optional[Request], code: str, ru: str, en: str, params: Optional[dict] = None) -> dict:
    """Сформировать канонический объект ошибки для API (error_code + detail + params)."""
    return {
        "error_code": code,
        "detail": tr(request, ru, en),
        "params": params or {},
    }
