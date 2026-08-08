"""Миграция 0001: Создание первичной схемы таблиц NMS-WebUI."""
import sqlite3

VERSION = 1
DESCRIPTION = "Initial schema creation"


def up(conn: sqlite3.Connection) -> None:
    """Применить миграцию первичного создания таблиц."""
    # 1. Роли
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            is_system BOOLEAN DEFAULT 0
        );
    """)

    # 2. Разрешения
    conn.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            module_id TEXT DEFAULT NULL
        );
    """)

    # 3. Связь ролей и разрешений
    conn.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id TEXT NOT NULL,
            permission_id TEXT NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
        );
    """)

    # 4. Пользователи
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL DEFAULT '',
            email TEXT,
            uid TEXT UNIQUE NOT NULL DEFAULT '',
            hashed_password TEXT NOT NULL DEFAULT '',
            is_active BOOLEAN DEFAULT 1,
            role_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            avatar TEXT,
            token_valid_after INTEGER DEFAULT 0,
            must_change_password BOOLEAN DEFAULT 0,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            title TEXT DEFAULT '',
            last_seen TIMESTAMP,
            mfa_enabled INTEGER DEFAULT 0,
            mfa_secret TEXT,
            mfa_recovery_codes TEXT,
            FOREIGN KEY (role_id) REFERENCES roles (id)
        );
    """)

    # 5. Журнал аудита
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id TEXT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            resource TEXT NOT NULL,
            details TEXT,
            ip_address TEXT
        );
    """)

    # 6. Системные настройки
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    # 7. Активные сессии
    conn.execute("""
        CREATE TABLE IF NOT EXISTS active_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_jti TEXT NOT NULL,
            refresh_jti TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_revoked BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
    """)

    # 8. Удаленные источники логов
    conn.execute("""
        CREATE TABLE IF NOT EXISTS remote_log_sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            api_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 9. Уведомления
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'info',
            category TEXT NOT NULL DEFAULT 'system',
            read BOOLEAN DEFAULT 0,
            link TEXT DEFAULT NULL,
            user_id TEXT DEFAULT NULL,
            acknowledged BOOLEAN DEFAULT 0,
            acknowledged_by TEXT DEFAULT NULL,
            acknowledged_at TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 10. Интеграции уведомлений
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_integrations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            min_type TEXT DEFAULT 'warning',
            categories TEXT DEFAULT '*',
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
