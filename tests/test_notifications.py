"""Тесты системы уведомлений ядра (notify.py, ModuleContext, API)."""
from __future__ import annotations

import time
import pytest
from pathlib import Path

from backend.core.database import init_db, get_db_connection
from backend.core.notify import (
    clear_read_notifications,
    cleanup_module_notifications,
    count_unread_notifications,
    delete_notification,
    get_user_notifications,
    mark_all_as_read,
    mark_as_read,
    notify,
    prune_notifications,
)
from backend.core.plugin.context import ModuleContext
from backend.core.bus import event_bus


@pytest.fixture(autouse=True)
def setup_test_db():
    """Подготовка тестовой БД перед каждым тестом."""
    init_db()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM notifications")
    finally:
        conn.close()


def test_notify_creation_and_reading():
    """Тест создания уведомления, сохранения в БД и получения списка."""
    res = notify(
        user_id="usr-test-1",
        title="Тестовое уведомление",
        body="Детали сообщения",
        severity="warning",
        entity_id="entity-123",
        module_id="core",
    )

    assert res["id"] > 0
    assert res["user_id"] == "usr-test-1"
    assert res["title"] == "Тестовое уведомление"
    assert res["severity"] == "warning"
    assert res["read_at"] is None

    # Непрочитанные
    assert count_unread_notifications("usr-test-1") == 1

    # Список
    data = get_user_notifications("usr-test-1")
    assert data["total"] == 1
    assert data["unread_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Тестовое уведомление"


def test_mark_as_read_and_mark_all_as_read():
    """Тест пометки как прочитанное одного и всех уведомлений."""
    n1 = notify("user-2", "Заголовок 1")
    n2 = notify("user-2", "Заголовок 2")

    assert count_unread_notifications("user-2") == 2

    # Пометить одно
    ok = mark_as_read(n1["id"], "user-2")
    assert ok is True
    assert count_unread_notifications("user-2") == 1

    # Повторная пометка прочитанного возвращает False
    ok_again = mark_as_read(n1["id"], "user-2")
    assert ok_again is False

    # Пометить все оставшиеся
    count = mark_all_as_read("user-2")
    assert count == 1
    assert count_unread_notifications("user-2") == 0


def test_delete_and_clear_read():
    """Тест удаления конкретного уведомления и очистки всех прочитанных."""
    n1 = notify("user-3", "Msg 1")
    n2 = notify("user-3", "Msg 2")

    mark_as_read(n1["id"], "user-3")

    # Clear read
    deleted_read = clear_read_notifications("user-3")
    assert deleted_read == 1

    # Проверяем, что осталось только n2
    data = get_user_notifications("user-3")
    assert data["total"] == 1
    assert data["items"][0]["id"] == n2["id"]

    # Удалить n2
    del_ok = delete_notification(n2["id"], "user-3")
    assert del_ok is True
    assert get_user_notifications("user-3")["total"] == 0


def test_module_context_notify_and_cleanup():
    """Тест вызова notify из ModuleContext и очистки при uninstall модуля."""
    ctx = ModuleContext(
        module_id="mod_telemetry",
        root=Path("/tmp"),
    )

    n = ctx.notify(
        user_id="user-4",
        title="Сбой датчика",
        body="Датчик #12 не отвечает",
        severity="error",
    )

    assert n["module_id"] == "mod_telemetry"
    assert n["severity"] == "error"

    # Создадим уведомление от другого модуля
    notify("user-4", "Системное", module_id="core")

    data = get_user_notifications("user-4")
    assert data["total"] == 2

    # Очистка ресурсов модуля
    cleaned = cleanup_module_notifications("mod_telemetry")
    assert cleaned == 1

    # Проверяем, что системное уведомление осталось, а модовое удалено
    data_after = get_user_notifications("user-4")
    assert data_after["total"] == 1
    assert data_after["items"][0]["module_id"] == "core"


def test_prune_old_notifications():
    """Тест автоочистки по retention периоду."""
    conn = get_db_connection()
    old_time = time.time() - (40 * 86400.0)  # 40 дней назад
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO notifications (module_id, user_id, title, body, severity, created_at, read_at)
                VALUES ('core', 'user-5', 'Старое сообщение', '', 'info', ?, NULL)
                """,
                (old_time,),
            )
    finally:
        conn.close()

    # Свежее уведомление
    notify("user-5", "Новое сообщение")

    assert get_user_notifications("user-5")["total"] == 2

    # Prune старше 30 дней
    pruned = prune_notifications(days=30)
    assert pruned == 1

    remaining = get_user_notifications("user-5")
    assert remaining["total"] == 1
    assert remaining["items"][0]["title"] == "Новое сообщение"


def test_event_bus_publishing():
    """Тест публикации события core.notifications.created в EventBus."""
    received = []

    def on_notification(topic, payload):
        received.append(payload)

    event_bus.subscribe("core.notifications.created", on_notification)
    try:
        notify("user-6", "Bus Title", "Bus Body")
        assert len(received) == 1
        assert received[0]["user_id"] == "user-6"
        assert received[0]["title"] == "Bus Title"
    finally:
        event_bus.unsubscribe("core.notifications.created", on_notification)
