"""Database initialization and SQLite connection pool.

Manages tables: users, roles, permissions, role_permissions, user_roles, audit_logs.
Uses Python stdlib sqlite3 and hashlib (PBKDF2-HMAC-SHA256) for zero external dependencies.
"""
from __future__ import annotations

import os
import json
import sqlite3
import hashlib
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = DATA_DIR / "nms.db"


def get_db_connection() -> sqlite3.Connection:
    """Получить соединение с SQLite базой данных."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Хеширование пароля с помощью PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100_000
    )
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Проверка пароля по хешу."""
    try:
        salt, _ = hashed_password.split('$', 1)
        return hash_password(password, salt) == hashed_password
    except Exception:
        return False


def init_db() -> None:
    """Создание таблиц и наполнение первично необходимыми данными."""
    conn = get_db_connection()
    try:
        with conn:
            # 1. Таблица ролей
            conn.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_system BOOLEAN DEFAULT 0
                );
            """)

            # 2. Таблица разрешений (permissions)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS permissions (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    module_id TEXT DEFAULT NULL
                );
            """)

            existing_perm_cols = {col["name"] for col in conn.execute("PRAGMA table_info(permissions)").fetchall()}
            if "module_id" not in existing_perm_cols:
                conn.execute("ALTER TABLE permissions ADD COLUMN module_id TEXT DEFAULT NULL")

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

            # 4. Таблица пользователей
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
                    FOREIGN KEY (role_id) REFERENCES roles (id)
                );
            """)

            # Автоматическая миграция для добавления отсутствующих полей
            existing_cols = {col["name"] for col in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "full_name" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT NOT NULL DEFAULT ''")
            if "email" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
            if "uid" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN uid TEXT NOT NULL DEFAULT ''")
            if "hashed_password" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN hashed_password TEXT NOT NULL DEFAULT ''")
            if "avatar" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
            if "token_valid_after" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN token_valid_after INTEGER DEFAULT 0")
            if "must_change_password" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0")
            if "failed_login_attempts" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0")
            if "locked_until" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN locked_until TIMESTAMP")
            if "title" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN title TEXT DEFAULT ''")
            if "last_seen" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN last_seen TIMESTAMP")
            if "mfa_enabled" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN mfa_enabled INTEGER DEFAULT 0")
            if "mfa_secret" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN mfa_secret TEXT")

            # 5. Таблица аудита логов
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

            # 6. Таблица системных настроек (key-value)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            # 7. Таблица активных сессий пользователей
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_jti TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_revoked BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                );
            """)



            # ── Инициализация начальных ролей ───────────────────
            default_roles = [
                ("1", "Superuser", "Полный доступ к системе и ее конфигурации", 1),
                ("2", "Admin", "Административный контроль, ограничение на удаление", 1),
                ("3", "Operator", "Управление конфигурациями и мониторингом", 1),
                ("4", "Viewer", "Только чтение параметров и логов", 1),
            ]
            for r_id, r_name, r_desc, r_sys in default_roles:
                conn.execute(
                    "INSERT OR IGNORE INTO roles (id, name, description, is_system) VALUES (?, ?, ?, ?)",
                    (r_id, r_name, r_desc, r_sys)
                )

            # ── Инициализация стандартных прав ──────────────────
            default_permissions = [
                ("system.all", "Система", "Полный доступ", "Полные права суперпользователя"),
                ("system.admin", "Система", "Администрирование", "Просмотр логов, бэкапы, управление сессиями"),
                ("users.view", "Пользователи", "Просмотр пользователей", "Просмотр списка пользователей и их данных"),
                ("users.manage", "Пользователи", "Управление пользователями", "Создание, редактирование и удаление пользователей"),
                ("roles.view", "Доступ", "Просмотр ролей", "Просмотр списка ролей и прав"),
                ("roles.manage", "Доступ", "Управление ролями", "Изменение матрицы прав доступа и создание ролей"),
                ("settings.view", "Настройки", "Просмотр настроек", "Просмотр системных настроек и конфигурации"),
                ("settings.edit", "Настройки", "Изменение настроек", "Редактирование параметров системы и модулей"),
                ("modules.view", "Модули", "Просмотр модулей", "Просмотр списка доступных модулей и статусов"),
                ("modules.manage", "Модули", "Управление модулями", "Включение и выключение плагинов"),
                ("audit.view", "Аудит", "Просмотр журнала аудита", "Доступ к событиям безопасности и журналам"),
                ("audit.export", "Аудит", "Экспорт аудита", "Экспорт журнала аудита безопасности"),
            ]
            for p_id, p_cat, p_name, p_desc in default_permissions:
                conn.execute(
                    "INSERT OR IGNORE INTO permissions (id, category, name, description) VALUES (?, ?, ?, ?)",
                    (p_id, p_cat, p_name, p_desc)
                )

            # Назначение всех прав роли Superuser
            for p_id, _, _, _ in default_permissions:
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('1', ?)",
                    (p_id,)
                )

            # Назначение прав роли Admin
            admin_perms = [
                "system.admin", "users.view", "users.manage", "roles.view", "roles.manage",
                "settings.view", "settings.edit", "modules.view", "modules.manage", "audit.view", "audit.export"
            ]
            for p_id in admin_perms:
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('2', ?)",
                    (p_id,)
                )

            # Назначение прав роли Operator
            operator_perms = ["users.view", "roles.view", "settings.view", "settings.edit", "modules.view", "audit.view"]
            for p_id in operator_perms:
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('3', ?)",
                    (p_id,)
                )

            # Назначение прав роли Viewer
            viewer_perms = ["users.view", "roles.view", "settings.view", "modules.view", "audit.view"]
            for p_id in viewer_perms:
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('4', ?)",
                    (p_id,)
                )

            # ── Автоматическая миграция admin -> root ──
            conn.execute("UPDATE users SET username = 'root', full_name = 'Главный администратор (Root)', uid = 'ROOT-001' WHERE username = 'admin'")

            # ── Инициализация системного пользователя root ──
            root_user = conn.execute("SELECT id FROM users WHERE username = 'root'").fetchone()
            if not root_user:
                pass_hash = hash_password("admin")
                conn.execute(
                    """
                    INSERT INTO users (id, username, full_name, email, uid, hashed_password, is_active, role_id)
                    VALUES (?, ?, ?, ?, ?, ?, 1, '1')
                    """,
                    ("usr-root-01", "root", "Главный администратор (Root)", "root@nms.local", "ROOT-001", pass_hash)
                )
    finally:
        conn.close()


def get_db():
    """Dependency для FastAPI."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_system_setting(key: str, default: Any = None) -> Any:
    """Получить системную настройку из БД."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT value FROM system_settings WHERE key = ?", (key,)).fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except Exception:
                return row["value"]
        return default
    finally:
        conn.close()


def set_system_setting(key: str, value: Any) -> None:
    """Сохранить системную настройку в БД."""
    conn = get_db_connection()
    try:
        val_str = json.dumps(value) if not isinstance(value, str) else value
        conn.execute(
            "INSERT INTO system_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, val_str),
        )
        conn.commit()
    finally:
        conn.close()

