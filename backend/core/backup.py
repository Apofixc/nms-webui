"""Автоматическое резервное копирование SQLite базы данных NMS-WebUI."""
from __future__ import annotations

import datetime
import logging
import sqlite3
from pathlib import Path

from backend.core.database import DATA_DIR, DB_PATH

_log = logging.getLogger("nms.backup")
BACKUPS_DIR = DATA_DIR / "backups"


def create_database_backup(retention_copies: int = 10) -> Path:
    """Создать атомарный бэкап базы данных SQLite в data/backups/ и ротировать старые копии."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUPS_DIR / f"nms_backup_{timestamp}.sqlite3"

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")

    # Атомарное резервное копирование SQLite в режиме WAL
    source_conn = sqlite3.connect(DB_PATH)
    dest_conn = sqlite3.connect(backup_file)
    try:
        with dest_conn:
            source_conn.backup(dest_conn)
        _log.info("Database backup created successfully: %s", backup_file)
    finally:
        source_conn.close()
        dest_conn.close()

    # Ротация старых бэкапов
    cleanup_old_backups(retention_copies=retention_copies)
    return backup_file


def cleanup_old_backups(retention_copies: int = 10) -> None:
    """Удалить старые копии бэкапов, оставив только последние retention_copies файлов."""
    if not BACKUPS_DIR.exists():
        return

    backups: list[Path] = sorted(
        [p for p in BACKUPS_DIR.glob("nms_backup_*.sqlite3") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if len(backups) > retention_copies:
        for old_backup in backups[retention_copies:]:
            try:
                old_backup.unlink()
                _log.info("Removed old database backup: %s", old_backup.name)
            except Exception as exc:
                _log.warning("Failed to remove old backup %s: %s", old_backup.name, exc)
