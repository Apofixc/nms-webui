"""Миграция 0002: Создание индексов для ускорения поиска и оптимизация связей."""
import sqlite3

VERSION = 2
DESCRIPTION = "Add performance indexes for audit_logs, active_sessions and notifications"


def up(conn: sqlite3.Connection) -> None:
    """Создать индексы производительности."""
    # Индексы журнала аудита
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);")

    # Индексы активных сессий
    conn.execute("CREATE INDEX IF NOT EXISTS idx_active_sessions_user_id ON active_sessions(user_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_active_sessions_token_jti ON active_sessions(token_jti);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_active_sessions_refresh_jti ON active_sessions(refresh_jti);")

    # Индексы уведомлений
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, read);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_read_id ON notifications(user_id, read, id DESC);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);")
