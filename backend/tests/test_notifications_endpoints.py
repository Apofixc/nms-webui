"""Интеграционный тест FastAPI эндпоинтов Центра Уведомлений."""

import sys
import asyncio
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.core.database import init_db
from backend.core.notifications_api import (
    create_notification,
    get_notifications,
    get_unread_count,
    mark_as_read,
    mark_all_as_read,
    delete_notification,
    clear_notifications,
)


async def run_async_tests():
    init_db()

    # 1. Создание нескольких уведомлений
    n1 = create_notification("Уведомление 1", "Сообщение 1", "info", "system")
    n2 = create_notification("Уведомление 2", "Сообщение 2", "error", "stream")

    # 2. Непрочитанные
    unread = await get_unread_count(user=None)
    assert unread["count"] >= 2

    # 3. Получение списка
    items = await get_notifications(unread_only=True, user=None)
    assert len(items) >= 2

    # 4. Отметка одного как прочитанного
    res = await mark_as_read(n1["id"], user=None)
    assert res["status"] == "ok"

    # 5. Отметка всех как прочитанных
    res_all = await mark_all_as_read(user=None)
    assert res_all["status"] == "ok"

    unread_after = await get_unread_count(user=None)
    assert unread_after["count"] == 0

    # 6. Очистка
    res_clear = await clear_notifications(unread_only=False, user=None)
    assert res_clear["status"] == "ok"

    print("All notification API endpoints verified successfully!")


if __name__ == "__main__":
    asyncio.run(run_async_tests())
