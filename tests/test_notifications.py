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
    get_notification_preferences,
    get_user_notifications,
    mark_all_as_read,
    mark_as_read,
    notify,
    prune_notifications,
    set_notification_preferences,
)
from backend.core.plugin.context import ModuleContext
from backend.core.bus import event_bus


@pytest.fixture(autouse=True)
def setup_test_db():
    """Подготовка тестовой БД перед каждым тестом."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DROP TABLE IF EXISTS notification_preferences")
            conn.execute("DELETE FROM notifications")
    finally:
        conn.close()
    init_db()


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
    """Тест пометки как прочитанное одного и всех уведомлений (идемпотентно)."""
    n1 = notify("user-2", "Заголовок 1")
    n2 = notify("user-2", "Заголовок 2")

    assert count_unread_notifications("user-2") == 2

    # Пометить одно
    ok = mark_as_read(n1["id"], "user-2")
    assert ok is True
    assert count_unread_notifications("user-2") == 1

    # Повторная пометка уже прочитанного уведомления идемпотентна и возвращает True для существующих
    ok_again = mark_as_read(n1["id"], "user-2")
    assert ok_again is True

    # Для несуществующего или чужого уведомления возвращается False
    assert mark_as_read(999999, "user-2") is False
    assert mark_as_read(n2["id"], "other-user") is False

    # Пометить все оставшиеся
    count = mark_all_as_read("user-2")
    assert count == 1
    assert count_unread_notifications("user-2") == 0


def test_notify_input_validation_and_normalization():
    """Тест очистки и нормализации входных данных в notify()."""
    res = notify(
        user_id="  usr-test-norm  ",
        title="  Нормализованный заголовок  ",
        severity="  WARNING  ",
        category="  SECURITY  ",
        module_id="  mod_custom  ",
    )
    assert res["user_id"] == "usr-test-norm"
    assert res["title"] == "Нормализованный заголовок"
    assert res["severity"] == "warning"
    assert res["category"] == "security"
    assert res["module_id"] == "mod_custom"

    # Кастомная/неизвестная категория автоматически фоллбэкается на 'system'
    res_unknown = notify("usr-test-norm", "Тест категории", category="unknown_category")
    assert res_unknown["category"] == "system"


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


def test_notification_preferences():
    """Тест чтения и сохранения предпочтений уведомлений."""
    prefs = get_notification_preferences("usr-pref-1")
    assert prefs["push_enabled"] is True
    assert prefs["sound_enabled"] is True
    assert prefs["subscribed_modules"] is None

    updated = set_notification_preferences(
        "usr-pref-1", push_enabled=False, sound_enabled=True, subscribed_modules=["core", "topology"]
    )
    assert updated["push_enabled"] is False
    assert updated["subscribed_modules"] == ["core", "topology"]

    fetched = get_notification_preferences("usr-pref-1")
    assert fetched["push_enabled"] is False
    assert fetched["sound_enabled"] is True
    assert fetched["subscribed_modules"] == ["core", "topology"]


def test_notify_module_subscriptions():
    """Тест фильтрации уведомлений по подпискам на модули."""
    # Подпишем user-7 только на core и topology
    set_notification_preferences("user-7", subscribed_modules=["core", "topology"])

    # Уведомление от неподписанного модуля devices должно возвращать None
    res1 = notify("user-7", "Аларм устройств", module_id="devices")
    assert res1 is None
    assert count_unread_notifications("user-7") == 0

    # Уведомление от подписанного модуля topology создается успешно
    res2 = notify("user-7", "Предупреждение топологии", module_id="topology")
    assert res2 is not None
    assert res2["module_id"] == "topology"
    assert count_unread_notifications("user-7") == 1


def test_notify_title_and_body_truncation():
    """Тест автоматической обрезки избыточно длинного заголовка и тела уведомления."""
    long_title = "A" * 300
    long_body = "B" * 5000

    res = notify("user-trunc", title=long_title, body=long_body)
    assert len(res["title"]) == 255
    assert res["title"].endswith("...")
    assert len(res["body"]) == 4000
    assert res["body"].endswith("...")


def test_notify_from_background_thread():
    """Тест безошибочного вызова notify() из стороннего фонового потока (threading.Thread)."""
    import threading

    result_container = []

    def worker():
        res = notify("user-thread", title="Из фонового потока", body="Текст")
        result_container.append(res)

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=3.0)

    assert len(result_container) == 1
    assert result_container[0]["user_id"] == "user-thread"
    assert count_unread_notifications("user-thread") == 1


def test_notify_with_target_url():
    """Тест сохранения и получения параметра target_url."""
    res = notify("user-url", title="Кликните здесь", target_url="/devices/dev-123")
    assert res["target_url"] == "/devices/dev-123"

    user_notifs = get_user_notifications("user-url")
    assert len(user_notifs["items"]) == 1
    assert user_notifs["items"][0]["target_url"] == "/devices/dev-123"


def test_get_notification_categories():
    """Тест получения доступных категорий уведомлений."""
    from backend.core.notify import get_notification_categories

    cats = get_notification_categories()
    assert "system" in cats
    assert "security" in cats
    assert "module" in cats
    assert "user" in cats


def test_get_notification_modules():
    """Тест получения доступных модулей системы для подписки."""
    from backend.core.notify import get_notification_modules

    mods = get_notification_modules()
    assert isinstance(mods, list)
    assert any(m["id"] == "core" for m in mods)


def test_notify_subscribed_modules():
    """Тест фильтрации по явным подпискам на модули."""
    # Явно подписываем пользователя user-sub на модуль telemetry
    set_notification_preferences("user-sub", subscribed_modules=["telemetry"])

    # Уведомление от модуля telemetry должно проходить
    n1 = notify("user-sub", "Данные телеметрии", module_id="telemetry")
    assert n1 is not None

    # Уведомление от не подписанного модуля syslog должно отсекаться
    n2 = notify("user-sub", "Лог сислога", module_id="syslog")
    assert n2 is None

    # Системное уведомление от ядра (core) должно проходить всегда
    n_core = notify("user-sub", "Системный аларм", module_id="core")
    assert n_core is not None


def test_notify_module_severity_threshold():
    """Тест фильтрации уведомлений по порогу важности (min_severity)."""
    set_notification_preferences(
        "user-sev",
        subscribed_modules=["telemetry"],
        module_rules={"telemetry": {"min_severity": "warning"}},
    )

    # info сообщение ниже порога warning — отсекается
    n_info = notify("user-sev", "Инфо", severity="info", module_id="telemetry")
    assert n_info is None

    # warning сообщение на пороге — проходит
    n_warn = notify("user-sev", "Варнинг", severity="warning", module_id="telemetry")
    assert n_warn is not None

    # error сообщение выше порога — проходит
    n_err = notify("user-sev", "Ошибка", severity="error", module_id="telemetry")
    assert n_err is not None


def test_notify_unstripped_user_id_operations():
    """Тест работы операций mark_all_as_read, delete_notification, clear_read_notifications с переданным ненормализованным user_id (с пробелами)."""
    uid_clean = "user-strip-test"
    uid_padded = "  user-strip-test  "

    n1 = notify(uid_padded, "Заголовок 1")
    n2 = notify(uid_clean, "Заголовок 2")
    assert n1 is not None
    assert n2 is not None

    # Пометка всех прочитанными с передачей padded uid
    marked = mark_all_as_read(uid_padded)
    assert marked == 2

    # Очистка прочитанных с padded uid
    cleared = clear_read_notifications(uid_padded)
    assert cleared == 2

    # Создание для теста индивидуального удаления
    n3 = notify(uid_clean, "Заголовок 3")
    assert n3 is not None
    deleted = delete_notification(n3["id"], uid_padded)
    assert deleted is True




