"""Русская локализация сообщений бэкенда."""
from __future__ import annotations

MESSAGES: dict[str, str] = {
    "audit_logs_rotated": "Удалено {deleted} устаревших записей аудита",
    "bulk_action": "Массовое действие {action} над пользователями ({count})",
    "password_too_short": "Пароль слишком короткий (минимальная длина: {min_len} символов)",
    "password_require_uppercase": "Пароль должен содержать хотя бы одну заглавную букву",
    "password_require_digits": "Пароль должен содержать хотя бы одну цифру",
    "password_require_special": "Пароль должен содержать хотя бы один специальный символ (!@#$%^&*)",
    "ip_access_denied": "Доступ с вашего IP-адреса ({client_ip}) запрещен политикой безопасности",
    "auth_required": "Необходима авторизация",
    "invalid_token": "Недействительный или просроченный токен",
    "user_not_found_or_locked": "Пользователь не найден или заблокирован",
    "session_revoked": "Сессия аннулирована. Выполните повторный вход",
    "insufficient_permissions": "Недостаточно прав доступа ({permission})",
    "module_disabled": "Модуль '{module_id}' отключен в системе",
    "db_file_not_found": "Файл базы данных не найден",
    "backup_file_empty": "Файл резервной копии пуст или не передан",
    "db_restored_success": "База данных успешно восстановлена",
    "log_provider_not_found": "Источник логов не найден",
    "all_sessions_terminated": "Все сторонние сессии пользователей успешно аннулированы",
}
