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
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception:
        pass
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


from backend.core.migrations.runner import apply_migrations


def init_db() -> None:
    """Создание таблиц через миграции и наполнение первично необходимыми данными."""
    conn = get_db_connection()
    try:
        # Применение всех невыполненных файловых миграций
        apply_migrations(conn)

        with conn:




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

            # ── Обновление стандартов привязок для системных ролей ──
            conn.execute("DELETE FROM role_permissions WHERE role_id IN ('1', '2', '3', '4')")

            # Назначение всех прав роли Superuser ('1')
            for p_id, _, _, _ in default_permissions:
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('1', ?)",
                    (p_id,)
                )

            # Назначение прав роли Admin ('2')
            admin_perms = [
                "system.admin", "users.view", "users.manage", "roles.view", "roles.manage",
                "settings.view", "settings.edit", "modules.view", "modules.manage", "audit.view", "audit.export"
            ]
            for p_id in admin_perms:
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('2', ?)",
                    (p_id,)
                )

            # Назначение прав роли Operator ('3'): доступ к настройкам и модулям, без управления пользователями и ролями
            operator_perms = ["settings.view", "settings.edit", "modules.view", "audit.view"]
            for p_id in operator_perms:
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES ('3', ?)",
                    (p_id,)
                )

            # Назначение прав роли Viewer ('4'): только чтение логов и аудита (без пользователей, ролей, модулей и системных настроек)
            viewer_perms = ["audit.view"]
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

            # ── Вызов автоочистки устаревших прочитанных уведомлений (TTL 30 дней) ──
            try:
                conn.execute(
                    "DELETE FROM notifications WHERE read = 1 AND datetime(created_at) < datetime('now', '-30 days')"
                )
            except Exception:
                pass
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


def cleanup_old_notifications(days: int = 30) -> int:
    """Автоматически удалить прочитанные уведомления старше указанных дней (TTL)."""
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM notifications WHERE read = 1 AND datetime(created_at) < datetime('now', ?)",
                (f"-{days} days",),
            )
            return cur.rowcount
    except Exception as exc:
        _log.error("Failed to cleanup old notifications: %s", exc)
        return 0
    finally:
        conn.close()


