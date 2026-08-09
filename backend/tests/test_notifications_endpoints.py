"""Интеграционный тест FastAPI эндпоинтов Центра Уведомлений."""

import sys
import asyncio
import pytest
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.core.database import init_db
from backend.api.notifications import (
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

    # 0. Проверка WAL режима SQLite
    from backend.core.database import get_db_connection
    conn = get_db_connection()
    try:
        row = conn.execute("PRAGMA journal_mode;").fetchone()
        assert row[0].lower() == "wal"
    finally:
        conn.close()

    # 1. Создание нескольких уведомлений
    n1 = create_notification("Уведомление 1", "Сообщение 1", "info", "system")
    n2 = create_notification("Уведомление 2", "Сообщение 2", "error", "stream")

    # 2. Непрочитанные
    unread = await get_unread_count(user=None)
    assert unread["count"] >= 2

    # 3. Получение списка
    items = await get_notifications(unread_only=True, user=None)
    assert len(items) >= 2

    # 3.5. Проверка поиска по ключевому слову
    search_res = await get_notifications(search="Сообщение 2", user=None)
    assert len(search_res) == 1
    assert search_res[0]["id"] == n2["id"]

    # 4. Отметка пачки уведомлений (read-batch)
    from backend.api.notifications import mark_read_batch, NotificationReadBatchPayload, acknowledge_notification
    batch_res = await mark_read_batch(NotificationReadBatchPayload(ids=[n1["id"], n2["id"]]), user=None)
    assert batch_res["status"] == "ok"
    assert batch_res["updated"] >= 1

    # 5. Проверка квитирования / приема аварии в работу (ack)
    ack_res = await acknowledge_notification(n2["id"], user=None)
    assert ack_res["id"] == n2["id"]
    assert ack_res["acknowledged"] is True

    # 6. Отметка всех как прочитанных
    res_all = await mark_all_as_read(user=None)
    assert res_all["status"] == "ok"

    unread_after = await get_unread_count(user=None)
    assert unread_after["count"] == 0

    # 7. Очистка
    res_clear = await clear_notifications(unread_only=False, user=None)
    assert res_clear["status"] == "ok"

    print("All notification API endpoints & WAL mode verified successfully!")


@pytest.mark.anyio
async def test_notifications_endpoints():
    await run_async_tests()


if __name__ == "__main__":
    asyncio.run(run_async_tests())
