"""Тесты для Центра Уведомлений."""

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.core.database import init_db, get_db_connection
from backend.core.notifications_api import create_notification


def test_notification_flow():
    init_db()

    # 1. Создание уведомления
    notif = create_notification(
        title="Тест",
        message="Сообщение",
        notification_type="info",
        category="system",
    )
    assert notif["id"] > 0
    assert notif["title"] == "Тест"
    assert notif["read"] is False

    # 2. Проверка создания уведомления для конкретного пользователя и ModuleContext.notify
    from backend.core.plugin.context import ModuleContext
    ctx = ModuleContext(module_id="tuya", root=Path("."))
    user_notif = ctx.notify(
        title="Персональное уведомление",
        message="Ошибка датчика",
        notification_type="error",
        user_id="usr-root-01",
    )
    assert user_notif["id"] > 0
    assert user_notif["category"] == "tuya"
    assert user_notif["user_id"] == "usr-root-01"

    # 3. Проверка записей в БД
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM notifications WHERE id = ?", (user_notif["id"],)).fetchone()
        assert row is not None
        assert row["title"] == "Персональное уведомление"
        assert row["user_id"] == "usr-root-01"
    finally:
        conn.close()


if __name__ == "__main__":
    test_notification_flow()
    print("Notification tests passed successfully!")
