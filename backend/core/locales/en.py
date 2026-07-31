"""Английская локализация сообщений бэкенда."""
from __future__ import annotations

MESSAGES: dict[str, str] = {
    "audit_logs_rotated": "Deleted {deleted} old audit records",
    "bulk_action": "Bulk action {action} on users ({count})",
    "password_too_short": "Password is too short (minimum length: {min_len} characters)",
    "password_require_uppercase": "Password must contain at least one uppercase letter",
    "password_require_digits": "Password must contain at least one digit",
    "password_require_special": "Password must contain at least one special character",
    "ip_access_denied": "Access from your IP address ({client_ip}) is restricted by security policy",
    "auth_required": "Authentication required",
    "invalid_token": "Invalid or expired token",
    "user_not_found_or_locked": "User not found or account is locked",
    "session_revoked": "Session revoked. Please log in again",
    "insufficient_permissions": "Insufficient permissions ({permission})",
    "module_disabled": "Module '{module_id}' is disabled",
    "db_file_not_found": "Database file not found",
    "backup_file_empty": "Backup file is empty or missing",
    "db_restored_success": "Database restored successfully",
    "log_provider_not_found": "Log provider not found",
    "all_sessions_terminated": "All user sessions terminated successfully",
}
