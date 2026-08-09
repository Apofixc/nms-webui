"""Unit tests for Core EventBus, ModuleContext event integration, and WS Bridge."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.core.bus import EventBus, match_topic
from backend.core.exceptions import PermissionDeniedError
from backend.core.plugin.context import ModuleContext, cleanup_module_events, get_module_events


def test_wildcard_matching():
    """Тестирование масок сопоставления топиков (match_topic)."""
    assert match_topic("core.*.enabled", "core.modules.enabled") is True
    assert match_topic("*.devices.down", "tuya.devices.down") is True
    assert match_topic("tuya.devices.*", "tuya.devices.status") is True
    assert match_topic("*", "any.topic.here") is True
    assert match_topic("#", "another.topic") is True
    assert match_topic("core.modules.enabled", "core.modules.enabled") is True

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

    assert delivered_count == 2
    assert len(received) == 1
    assert received[0] == ("test.event", {"key": "val"})


def test_core_topic_protection():
    """Запрет публикации в топики core.* из неядерного кода."""
    bus = EventBus()

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
    """Тестирование трансляции событий из EventBus в WebSocket Broadcaster."""
    from backend.core.bus import EventBus
    from backend.core.events import EventBusWsBridge

    test_bus = EventBus()
    mock_broadcaster = MagicMock()

    bridge = EventBusWsBridge(allowed_patterns=["*"])
    with patch("backend.core.bus.event_bus", test_bus), patch("backend.core.events.broadcaster", mock_broadcaster):
        bridge.setup()
        test_bus.publish("tuya.devices.status", {"online": True}, is_core=True)

        mock_broadcaster.broadcast.assert_called_once_with(
            data_dict={"type": "bus_event", "topic": "tuya.devices.status", "payload": {"online": True}},
            topic="tuya.devices.status",
            immediate=True,
        )
