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
