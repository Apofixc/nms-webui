"""Backend i18n helper utilities."""
from __future__ import annotations

from typing import Optional
from fastapi import Request


BACKEND_MESSAGES: dict[str, dict[str, str]] = {
    "audit_logs_rotated": {
        "ru": "Удалено {deleted} устаревших записей аудита",
        "en": "Deleted {deleted} old audit records",
    },
    "bulk_action": {
        "ru": "Массовое действие {action} над пользователями ({count})",
        "en": "Bulk action {action} on users ({count})",
    },
    "password_too_short": {
        "ru": "Пароль слишком короткий (минимальная длина: {min_len} символов)",
        "en": "Password is too short (minimum length: {min_len} characters)",
    },
    "password_require_uppercase": {
        "ru": "Пароль должен содержать хотя бы одну заглавную букву",
        "en": "Password must contain at least one uppercase letter",
    },
    "password_require_digits": {
        "ru": "Пароль должен содержать хотя бы одну цифру",
        "en": "Password must contain at least one digit",
    },
    "password_require_special": {
        "ru": "Пароль должен содержать хотя бы один специальный символ (!@#$%^&*)",
        "en": "Password must contain at least one special character",
    },
    "ip_access_denied": {
        "ru": "Доступ с вашего IP-адреса ({client_ip}) запрещен политикой безопасности",
        "en": "Access from your IP address ({client_ip}) is restricted by security policy",
    },
    "auth_required": {
        "ru": "Необходима авторизация",
        "en": "Authentication required",
    },
    "invalid_token": {
        "ru": "Недействительный или просроченный токен",
        "en": "Invalid or expired token",
    },
    "user_not_found_or_locked": {
        "ru": "Пользователь не найден или заблокирован",
        "en": "User not found or account is locked",
    },
    "session_revoked": {
        "ru": "Сессия аннулирована. Выполните повторный вход",
        "en": "Session revoked. Please log in again",
    },
    "insufficient_permissions": {
        "ru": "Недостаточно прав доступа ({permission})",
        "en": "Insufficient permissions ({permission})",
    },
    "module_disabled": {
        "ru": "Модуль '{module_id}' отключен в системе",
        "en": "Module '{module_id}' is disabled",
    },
    "db_file_not_found": {
        "ru": "Файл базы данных не найден",
        "en": "Database file not found",
    },
    "backup_file_empty": {
        "ru": "Файл резервной копии пуст или не передан",
        "en": "Backup file is empty or missing",
    },
    "db_restored_success": {
        "ru": "База данных успешно восстановлена",
        "en": "Database restored successfully",
    },
    "log_provider_not_found": {
        "ru": "Источник логов не найден",
        "en": "Log provider not found",
    },
    "all_sessions_terminated": {
        "ru": "Все сторонние сессии пользователей успешно аннулированы",
        "en": "All user sessions terminated successfully",
    },
}


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

