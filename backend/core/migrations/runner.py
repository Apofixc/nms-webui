"""Раннер применения файловых миграций SQLite базы данных NMS-WebUI."""
from __future__ import annotations

import importlib
import logging
import re
import sqlite3
from pathlib import Path
from typing import List, Tuple

_log = logging.getLogger("nms.migrations")
MIGRATIONS_DIR = Path(__file__).resolve().parent


def ensure_schema_migrations_table(conn: sqlite3.Connection) -> None:
    """Создать системную таблицу учета примененных миграций."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)


def get_applied_versions(conn: sqlite3.Connection) -> set[int]:
    """Получить множество примененных номеров миграций."""
    ensure_schema_migrations_table(conn)
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def discover_migrations() -> List[Tuple[int, str, Path]]:
    """Найти и отсортировать все файлы миграций формата 0001_description.py."""
    migrations = []
    pattern = re.compile(r"^(\d{4})_(.+)\.py$")
    if not MIGRATIONS_DIR.exists():
        return migrations

    for p in MIGRATIONS_DIR.iterdir():
        if p.is_file():
            match = pattern.match(p.name)
            if match:
                version = int(match.group(1))
                desc = match.group(2).replace("_", " ").title()
                migrations.append((version, desc, p))

    migrations.sort(key=lambda m: m[0])
    return migrations


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Применить незавершенные файловые миграции по порядку. Возвращает количество примененных."""
    ensure_schema_migrations_table(conn)
    applied_set = get_applied_versions(conn)
    all_migrations = discover_migrations()

    applied_count = 0
    for version, desc, path in all_migrations:
        if version in applied_set:
            continue

        _log.info("Applying migration %04d: %s", version, desc)
        module_name = f"backend.core.migrations.{path.stem}"
        try:
            mod = importlib.import_module(module_name)
            if not hasattr(mod, "up"):
                _log.error("Migration %s has no 'up' function", path.name)
                continue

            with conn:
                mod.up(conn)
                migration_desc = getattr(mod, "DESCRIPTION", desc)
                conn.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                    (version, migration_desc),
                )
            applied_count += 1
            _log.info("Migration %04d applied successfully", version)
        except Exception as exc:
            _log.error("Failed to apply migration %04d (%s): %s", version, path.name, exc, exc_info=True)
            raise RuntimeError(f"Migration {version} failed: {exc}") from exc

    return applied_count
