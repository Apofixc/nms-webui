"""Backend i18n helper utilities."""
from __future__ import annotations

from typing import Optional
from pathlib import Path
from fastapi import Request


from backend.core.locales import BACKEND_MESSAGES



def get_lang(request: Optional[Request]) -> str:
    """Извлечь язык из параметров запроса или заголовков HTTP. По умолчанию 'en'."""
    if not request:
        return "en"
    query_lang = request.query_params.get("lang", "").lower()
    if query_lang in ("ru", "en"):
        return query_lang
    accept = request.headers.get("accept-language", "").lower()
    if "ru" in accept:
        return "ru"
    return "en"


def tr(request: Optional[Request], key_or_ru: str, en: Optional[str] = None, **kwargs) -> str:
    """
    Вернуть локализованную строку по ключу или (ru, en) паре.
    Поддерживает подстановку параметров через kwargs.
    """
    lang = get_lang(request)
    if key_or_ru in BACKEND_MESSAGES:
        msg_dict = BACKEND_MESSAGES[key_or_ru]
        template = msg_dict.get(lang, msg_dict.get("en", key_or_ru))
        return template.format(**kwargs) if kwargs else template

    if en is not None:
        raw_text = key_or_ru if lang == "ru" else en
        return raw_text.format(**kwargs) if kwargs else raw_text

    return key_or_ru.format(**kwargs) if kwargs else key_or_ru


def make_error_detail(request: Optional[Request], code: str, ru_or_key: str, en: Optional[str] = None, params: Optional[dict] = None, **kwargs) -> dict:
    """Сформировать канонический объект ошибки для API (error_code + detail + params)."""
    p = params or {}
    p.update(kwargs)
    return {
        "error_code": code,
        "detail": tr(request, ru_or_key, en, **p),
        "params": p,
    }


def register_module_messages(messages: dict[str, dict[str, str]]) -> None:
    """Зарегистрировать или обновить переводы сообщений для модуля."""
    for key, lang_map in messages.items():
        if key not in BACKEND_MESSAGES:
            BACKEND_MESSAGES[key] = {}
        BACKEND_MESSAGES[key].update(lang_map)


def load_module_locales(module_dir: str | Path) -> None:
    """Автоматическая загрузка JSON/YAML файлов локализации из папки locales/ модуля."""
    import json
    from pathlib import Path
    path = Path(module_dir) / "locales"
    if not path.is_dir():
        return
    for json_file in path.glob("*.json"):
        lang = json_file.stem.lower()
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    register_module_messages({
                        key: {lang: str(val)} for key, val in data.items()
                    })
        except Exception:
            pass
