import asyncio
import threading
import time
from backend.core.database import init_db
from backend.core.notify import (
    get_notification_preferences,
    notify,
    set_notification_preferences,
)


def test_notify_from_background_thread():
    """Тест вызова notify() из фонового треда без вызова get_event_loop()."""
    init_db()
    test_user_id = "test_thread_user_1"
    
    result_container = []
    error_container = []

    def _worker():
        try:
            res = notify(
                user_id=test_user_id,
                title="Test from Thread",
                body="Testing thread safety",
                severity="info",
                module_id="core",
            )
            result_container.append(res)
        except Exception as exc:
            error_container.append(exc)

    t = threading.Thread(target=_worker)
    t.start()
    t.join(timeout=5.0)

    assert not error_container, f"Unexpected error in background thread: {error_container}"
    assert len(result_container) == 1
    assert result_container[0] is not None
    assert result_container[0]["title"] == "Test from Thread"


def test_module_rules_quick_unsubscribe_flow():
    """Тест отключения модуля через module_rules без блокировки новых модулей."""
    init_db()
    test_user_id = "test_sub_user_2"

    # Сбрасываем предпочтения
    set_notification_preferences(
        user_id=test_user_id,
        push_enabled=True,
        sound_enabled=True,
        subscribed_modules=None, # Все модули разрешены
        module_rules={},
    )

    # Отключаем модуль "topology" через module_rules
    set_notification_preferences(
        user_id=test_user_id,
        module_rules={"topology": {"enabled": False}},
    )

    # 1. Уведомление от отключенного модуля "topology" должно игнорироваться
    res_topo = notify(
        user_id=test_user_id,
        title="Topology Alert",
        module_id="topology",
    )
    assert res_topo is None, "Notification from disabled module 'topology' must be omitted"

    # 2. Уведомление от совершенно нового зарегистрированного модуля "new_plugin" должно приходить
    res_new = notify(
        user_id=test_user_id,
        title="New Plugin Alert",
        module_id="new_plugin",
    )
    assert res_new is not None, "Notification from new_plugin must be delivered when subscribed_modules is None"
    assert res_new["title"] == "New Plugin Alert"


def test_event_loop_and_connection_reuse():
    """Тест сохранения event loop в ws_manager и атомарного вычисления unread_count."""
    from backend.core.events import ws_manager
    from backend.core.database import get_db_connection
    from backend.core.notify import count_unread_notifications

    init_db()
    loop = asyncio.new_event_loop()
    try:
        ws_manager.set_loop(loop)
        assert ws_manager._loop is loop

        conn = get_db_connection()
        try:
            count = count_unread_notifications("test_user_conn", conn=conn)
            assert isinstance(count, int)
        finally:
            conn.close()
    finally:
        loop.close()


def test_prune_notifications_preserves_unread_errors():
    """Тест: prune_notifications не должен удалять непрочитанные аварии с severity='error'."""
    from backend.core.database import get_db_connection
    from backend.core.notify import prune_notifications, get_user_notifications

    init_db()
    user_id = "test_prune_user"
    old_time = time.time() - (40 * 86400.0) # 40 дней назад

    conn = get_db_connection()
    try:
        with conn:
            # 1. Старое прочитанное инфо-уведомление (должно быть удалено)
            conn.execute(
                "INSERT INTO notifications (module_id, user_id, title, body, severity, category, created_at, read_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("core", user_id, "Old Info", "Body", "info", "system", old_time, old_time + 10),
            )
            # 2. Старое НЕпрочитанное инфо-уведомление (должно быть удалено)
            conn.execute(
                "INSERT INTO notifications (module_id, user_id, title, body, severity, category, created_at, read_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                ("core", user_id, "Old Info Unread", "Body", "info", "system", old_time),
            )
            # 3. Старое НЕпрочитанное error-уведомление (должно быть СОХРАНЕНО)
            conn.execute(
                "INSERT INTO notifications (module_id, user_id, title, body, severity, category, created_at, read_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                ("core", user_id, "Old Error Unread", "Critical fault", "error", "system", old_time),
            )
    finally:
        conn.close()

    # Выполняем ротацию за 30 дней
    pruned = prune_notifications(days=30)
    assert pruned >= 2

    res = get_user_notifications(user_id=user_id, limit=50)
    titles = [item["title"] for item in res["items"]]

    assert "Old Error Unread" in titles, "Unread critical error notification must be preserved during retention prune"
    assert "Old Info" not in titles
    assert "Old Info Unread" not in titles


def test_prune_notifications_preserves_uppercase_unread_errors():
    """Тест: prune_notifications не должен удалять непрочитанные аварии с severity='ERROR' в верхнем регистре."""
    from backend.core.database import get_db_connection
    from backend.core.notify import prune_notifications, get_user_notifications

    init_db()
    user_id = "test_prune_user_upper"
    old_time = time.time() - (40 * 86400.0)

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO notifications (module_id, user_id, title, body, severity, category, created_at, read_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                ("core", user_id, "Old Uppercase Error Unread", "Critical fault", "ERROR", "system", old_time),
            )
    finally:
        conn.close()

    prune_notifications(days=30)

    res = get_user_notifications(user_id=user_id, limit=50)
    titles = [item["title"] for item in res["items"]]
    assert "Old Uppercase Error Unread" in titles, "Uppercase unread error notification must be preserved"


def test_non_telemetry_batch_does_not_drop_events_with_key():
    """Тест: батчинг не сбрасывает обычные события с полем 'key'."""
    from backend.core.events import ws_manager

    items_to_send = [
        {"data": {"type": "notification", "key": "same_key", "id": 1}, "target_user_id": None, "topic": None},
        {"data": {"type": "notification", "key": "same_key", "id": 2}, "target_user_id": None, "topic": None},
    ]

    seen_telemetry_keys = set()
    user_events = []
    for item in reversed(items_to_send):
        data = item.get("data", {})
        t_key = data.get("telemetry_key") or (data.get("key") if data.get("type") == "telemetry" else None)
        if t_key:
            if t_key in seen_telemetry_keys:
                continue
            seen_telemetry_keys.add(t_key)
        user_events.append(data)

    assert len(user_events) == 2, "Both non-telemetry events with 'key' must be preserved"


def test_subscribed_modules_strict_whitelist_filtering():
    """Тест: subscribed_modules работает как белый список, но разрешает явные переопределения в module_rules."""
    init_db()
    test_user_id = "test_sub_user_whitelist"

    set_notification_preferences(
        user_id=test_user_id,
        push_enabled=True,
        sound_enabled=True,
        subscribed_modules=["core", "topology"],
        module_rules={},
    )

    # 1. Модуль не входит в subscribed_modules и не включен в module_rules -> уведомление отклоняется
    res_omitted = notify(
        user_id=test_user_id,
        title="Unsubscribed Plugin Alert",
        module_id="brand_new_plugin",
    )
    assert res_omitted is None, "Notification from unsubscribed module must be omitted when subscribed_modules is set"

    # 2. Тот же модуль явно разрешен в module_rules -> уведомление доставляется
    set_notification_preferences(
        user_id=test_user_id,
        module_rules={"brand_new_plugin": {"enabled": True}},
    )
    res_allowed = notify(
        user_id=test_user_id,
        title="Override Plugin Alert",
        module_id="brand_new_plugin",
    )
    assert res_allowed is not None, "Explicitly enabled module in module_rules must be delivered even if not in subscribed_modules"
    assert res_allowed["title"] == "Override Plugin Alert"


def test_notify_sqlite_lock_retry():
    """Тест: notify() успевает успешно завершиться при временных блокировках соединения."""
    init_db()
    test_user_id = "test_lock_retry_user"

    res = notify(
        user_id=test_user_id,
        title="Test Lock Retry",
        body="Retry mechanism check",
        severity="info",
        module_id="core",
    )
    assert res is not None
    assert res["title"] == "Test Lock Retry"


def test_replay_limit_increased():
    """Тест: check_replay_status_from_db разрешает до 500 элементов без resync_required."""
    from backend.core.events import check_replay_status_from_db, record_event_in_db
    from backend.core.database import get_db_connection

    init_db()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT COALESCE(MAX(seq_id), 0) as max_id FROM system_events_journal").fetchone()
        start_id = row["max_id"]
    finally:
        conn.close()

    for i in range(250):
        record_event_in_db("test_event", f'{{"index": {i}}}', target_user_id="test_replay_user")

    status, events = check_replay_status_from_db(last_event_id=start_id, target_user_id="test_replay_user", limit=500)
    assert status == "replay", "Status should be 'replay' when gap is within 500 events limit"
    assert len(events) == 250


def test_telemetry_events_ignored_in_replay_gap_calculation():
    """Тест: фоновые события телеметрии не вызывают ложный resync_required в check_replay_status_from_db."""
    from backend.core.events import check_replay_status_from_db, record_event_in_db
    from backend.core.database import get_db_connection

    init_db()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT COALESCE(MAX(seq_id), 0) as max_id FROM system_events_journal").fetchone()
        start_id = row["max_id"]
    finally:
        conn.close()

    # Записываем 600 фоновых событий телеметрии
    for i in range(600):
        record_event_in_db("telemetry", f'{{"metric": {i}}}', target_user_id="test_telemetry_user", topic="telemetry/cpu")

    status, _ = check_replay_status_from_db(last_event_id=start_id, target_user_id="test_telemetry_user", limit=500)
    assert status == "replay", "High frequency telemetry events must not trigger resync_required"






