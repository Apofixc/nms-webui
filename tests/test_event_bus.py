"""Unit tests for Core EventBus, ModuleContext event integration, and WS Bridge."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.api.events import can_subscribe_to_topic
from backend.core.bus import EventBus, match_topic
from backend.core.exceptions import PermissionDeniedError
from backend.core.plugin.context import ModuleContext, cleanup_module_events


def test_wildcard_matching():
    """Тестирование масок сопоставления топиков (match_topic) в стиле MQTT (+ / # / *)."""
    assert match_topic("core.*.enabled", "core.modules.enabled") is True
    assert match_topic("*.devices.down", "tuya.devices.down") is True
    assert match_topic("tuya.devices.*", "tuya.devices.status") is True
    assert match_topic("*", "any.topic.here") is True
    assert match_topic("#", "another.topic") is True
    assert match_topic("core.modules.enabled", "core.modules.enabled") is True

    # Односегментные и многосегментные маски
    assert match_topic("a.*", "a.b") is True
    assert match_topic("a.*", "a") is False
    assert match_topic("a.*", "a.b.c") is False

    assert match_topic("a.#", "a") is True
    assert match_topic("a.#", "a.b") is True
    assert match_topic("a.#", "a.b.c.d") is True

    assert match_topic("a.+.c", "a.b.c") is True
    assert match_topic("a.+.c", "a.b.d.c") is False

    # Несовпадающие топики
    assert match_topic("core.*.enabled", "core.modules.disabled") is False
    assert match_topic("tuya.devices.down", "astra.devices.down") is False


def test_bus_publish_subscribe_and_error_isolation():
    """Тестирование публикации, подписки и изоляции ошибок обработчиков."""
    bus = EventBus()
    received = []

    def bad_handler(topic, payload):
        raise RuntimeError("Failing subscriber handler")

    def good_handler(topic, payload):
        received.append((topic, payload))

    bus.subscribe("test.*", bad_handler)
    bus.subscribe("test.*", good_handler)

    # Публикация события должна доставить его в good_handler, несмотря на падение bad_handler
    delivered_count = bus.publish("test.event", {"key": "val"}, is_core=True)

    assert delivered_count == 1
    assert len(received) == 1
    assert received[0] == ("test.event", {"key": "val"})


def test_core_topic_protection():
    """Запрет публикации в топики core.* из неядерного кода и безопасный дефолт is_core=False."""
    bus = EventBus()

    # По умолчанию is_core=False, поэтому вызов без is_core=True падает для core.*
    with pytest.raises(PermissionDeniedError):
        bus.publish("core.modules.enabled", {"module_id": "fake"})

    with pytest.raises(PermissionDeniedError):
        bus.publish("core.modules.enabled", {"module_id": "fake"}, is_core=False)

    # Публикация с is_core=True должна успешно выполняться
    assert bus.publish("core.modules.enabled", {"module_id": "fake"}, is_core=True) == 0


def test_module_context_events_prefixing_and_protection(tmp_path: Path):
    """Тестирование подстановки module_id и защиты core.* в контексте модуля."""
    bus = EventBus()
    received = []

    def handler(topic, payload):
        received.append((topic, payload))

    bus.subscribe("test_mod.devices.down", handler)

    ctx = ModuleContext(module_id="test_mod", root=tmp_path)

    # Запрет публикации в core.* от имени модуля
    with pytest.raises(PermissionDeniedError):
        ctx.events.publish("core.something", {"data": 1})

    # Автоподстановка префикса модуля: 'devices.down' -> 'test_mod.devices.down'
    with patch("backend.core.bus.event_bus", bus):
        ctx.events.publish("devices.down", {"status": "offline"})

    assert len(received) == 1
    assert received[0] == ("test_mod.devices.down", {"status": "offline"})


def test_auto_cleanup_module_subscriptions(tmp_path: Path):
    """Тестирование автоматической очистки подписок модуля при отмене/выгрузке."""
    bus = EventBus()
    received = []

    def handler(topic, payload):
        received.append(payload)

    with patch("backend.core.bus.event_bus", bus):
        ctx = ModuleContext(module_id="cleanup_mod", root=tmp_path)
        ctx.events.subscribe("sensor.data", handler)

        bus.publish("sensor.data", 100, is_core=True)
        assert len(received) == 1

        # Выгружаем/очищаем подписки модуля
        cleanup_module_events("cleanup_mod")

        bus.publish("sensor.data", 200, is_core=True)
        assert len(received) == 1  # Новое событие не получено


def test_ws_bridge_integration():
    """Тестирование трансляции событий из EventBus в WebSocket Broadcaster и защиты core.*."""
    from backend.core.bus import EventBus
    from backend.core.events import EventBusWsBridge

    test_bus = EventBus()
    mock_broadcaster = MagicMock()

    bridge = EventBusWsBridge(allowed_patterns=["*"], allow_core=False)
    with patch("backend.core.bus.event_bus", test_bus), patch("backend.core.events.broadcaster", mock_broadcaster):
        bridge.setup()
        test_bus.publish("modules.devices.status", {"online": True}, is_core=True)

        mock_broadcaster.broadcast.assert_called_once_with(
            data_dict={"type": "bus_event", "topic": "modules.devices.status", "payload": {"online": True}},
            topic="modules.devices.status",
            immediate=True,
        )

        mock_broadcaster.reset_mock()
        # События core.* не должны транслироваться в сокеты
        test_bus.publish("core.users.login", {"user_id": 1}, is_core=True)
        mock_broadcaster.broadcast.assert_not_called()


def test_can_subscribe_to_core_topic_protection():
    """Запрет подписки на core.* топики через WebSocket для обычных пользователей."""
    with patch("backend.api.events.get_security_settings", return_value={"auth_enabled": True}):
        with patch("backend.core.auth.user_has_permission", return_value=False):
            assert can_subscribe_to_topic("user-123", "core.users.login") is False
            assert can_subscribe_to_topic("user-123", "core.modules.status") is False
            assert can_subscribe_to_topic("user-123", "modules.status") is True

        with patch("backend.core.auth.user_has_permission", side_effect=lambda u, p: p == "system.admin"):
            assert can_subscribe_to_topic("admin-user", "core.users.login") is True


def test_subscriber_with_default_args_and_unsubscribe():
    """Проверка корректной передачи payload обработчикам с дефолтными аргументами и отписки."""
    bus = EventBus()
    received = []

    def handler_with_default(payload, extra=True):
        received.append((payload, extra))

    bus.subscribe("custom.topic", handler_with_default)
    bus.publish("custom.topic", {"data": 42})

    assert len(received) == 1
    assert received[0] == ({"data": 42}, True)

    # Отписка по функции
    assert bus.unsubscribe(handler_with_default) is True
    bus.publish("custom.topic", {"data": 43})
    assert len(received) == 1


@pytest.mark.anyio
async def test_bus_stats_clear_and_shutdown():
    """Тестирование получения статистики, очистки и асинхронной остановки (shutdown)."""
    import asyncio

    bus = EventBus()
    task_ran = False

    async def async_handler(payload):
        nonlocal task_ran
        await asyncio.sleep(0.01)
        task_ran = True

    bus.subscribe("async.topic", async_handler)

    stats = bus.get_stats()
    assert stats["subscribers_count"] == 1
    assert stats["patterns_count"] == 1
    assert "async.topic" in stats["patterns"]

    bus.publish("async.topic", "test_payload")
    # Ожидаем завершения или shutdown
    await bus.shutdown(timeout=1.0)

    assert task_ran is True
    assert bus.get_stats()["subscribers_count"] == 0


def test_varargs_subscriber():
    """Тестирование обработки подписчика с аргументами *args."""
    bus = EventBus()
    received = []

    def varargs_handler(*args):
        received.append(args)

    bus.subscribe("varargs.topic", varargs_handler)
    bus.publish("varargs.topic", {"key": "value"})

    assert len(received) == 1
    assert received[0] == ("varargs.topic", {"key": "value"})


def test_exact_topic_indexing():
    """Тестирование корректного разделения и O(1) индексации точечных топиков и масок."""
    bus = EventBus()
    exact_received = []
    wildcard_received = []

    def exact_handler(payload):
        exact_received.append(payload)

    def wildcard_handler(topic, payload):
        wildcard_received.append((topic, payload))

    bus.subscribe("device.status", exact_handler)
    bus.subscribe("device.*", wildcard_handler)

    assert len(bus._exact_subscribers.get("device.status", [])) == 1
    assert len(bus._wildcard_subscribers) == 1

    bus.publish("device.status", "online")

    assert exact_received == ["online"]
    assert wildcard_received == [("device.status", "online")]

    # Отписка от точечного топика переиндексирует словари
    bus.unsubscribe(exact_handler)
    assert len(bus._exact_subscribers.get("device.status", [])) == 0

    bus.publish("device.status", "offline")
    assert exact_received == ["online"]
    assert len(wildcard_received) == 2


@pytest.mark.anyio
async def test_concurrent_async_task_tracking():
    """Проверка безопасности _background_tasks при параллельном завершении задач."""
    import asyncio

    bus = EventBus()
    counter = 0

    async def async_slow_handler(payload):
        nonlocal counter
        await asyncio.sleep(0.01)
        counter += 1

    bus.subscribe("parallel.topic", async_slow_handler)

    for i in range(10):
        bus.publish("parallel.topic", i)

    # В процессе работы get_stats не должен выбрасывать RuntimeError
    stats = bus.get_stats()
    assert stats["active_tasks_count"] <= 10

    await bus.shutdown(timeout=1.0)
    assert counter == 10
    assert bus.get_stats()["active_tasks_count"] == 0



