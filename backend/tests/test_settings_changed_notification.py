import pytest
from backend.core.events import notify_settings_changed
from backend.core.database import get_db_connection
from backend.core.notify import get_user_notifications

def test_notify_settings_changed_creates_system_notification(tmp_path, monkeypatch):
    db_file = tmp_path / "test_nms.db"
    monkeypatch.setattr("backend.core.database.DB_PATH", db_file)

    conn = get_db_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT,
                severity TEXT DEFAULT 'info',
                category TEXT DEFAULT 'system',
                entity_id TEXT,
                target_url TEXT,
                created_at REAL NOT NULL,
                read_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                user_id TEXT PRIMARY KEY,
                push_enabled INTEGER DEFAULT 1,
                sound_enabled INTEGER DEFAULT 1,
                subscribed_modules TEXT,
                module_rules TEXT,
                sound_signals TEXT DEFAULT '{}'
            )
        """)
        conn.execute("INSERT INTO users (id, username, is_active) VALUES ('1', 'admin', 1)")
        conn.execute("INSERT INTO users (id, username, is_active) VALUES ('2', 'operator', 1)")
        conn.execute("INSERT INTO users (id, username, is_active) VALUES ('3', 'disabled_user', 0)")
    conn.close()

    notify_settings_changed("test_module")

    notifs_admin = get_user_notifications("1")
    assert notifs_admin["total"] == 1
    assert notifs_admin["items"][0]["module_id"] == "test_module"
    assert "Изменены настройки модуля 'test_module'" in notifs_admin["items"][0]["title"]

    notifs_op = get_user_notifications("2")
    assert notifs_op["total"] == 1

    notifs_disabled = get_user_notifications("3")
    assert notifs_disabled["total"] == 0
