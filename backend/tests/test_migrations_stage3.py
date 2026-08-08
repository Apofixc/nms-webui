"""Тесты для Этапа 3 (Система миграций БД)."""
import sqlite3

from backend.core.database import init_db
from backend.core.migrations.runner import (
    apply_migrations,
    discover_migrations,
    get_applied_versions,
)


def test_discover_migrations():
    """Проверка обнаружения файлов миграций."""
    migrations = discover_migrations()
    assert len(migrations) >= 2
    versions = [m[0] for m in migrations]
    assert 1 in versions
    assert 2 in versions
    assert versions == sorted(versions)


def test_apply_migrations_fresh_db(tmp_path):
    """Проверка применения миграций на чистой базе данных."""
    db_file = tmp_path / "test_mig.db"
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row

    applied_count = apply_migrations(conn)
    assert applied_count >= 2

    # Проверяем таблицу schema_migrations
    applied = get_applied_versions(conn)
    assert 1 in applied
    assert 2 in applied

    # Проверяем наличие ключевых таблиц
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "users" in tables
    assert "roles" in tables
    assert "audit_logs" in tables
    assert "notifications" in tables
    assert "schema_migrations" in tables

    # Повторный запуск должен вернуть 0 (идемпотентность)
    second_run = apply_migrations(conn)
    assert second_run == 0

    conn.close()


def test_init_db_creates_and_seeds(tmp_path, monkeypatch):
    """Проверка работы init_db с вызовом миграций и заполнением seed-данных."""
    fake_db = tmp_path / "nms_seed.db"
    monkeypatch.setattr("backend.core.database.DB_PATH", fake_db)

    init_db()
    assert fake_db.exists()

    conn = sqlite3.connect(fake_db)
    conn.row_factory = sqlite3.Row
    root_user = conn.execute("SELECT username FROM users WHERE username = 'root'").fetchone()
    assert root_user is not None
    assert root_user["username"] == "root"

    roles = conn.execute("SELECT COUNT(*) as cnt FROM roles").fetchone()["cnt"]
    assert roles >= 4
    conn.close()
