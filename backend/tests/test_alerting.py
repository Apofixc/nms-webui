"""Интеграционные тесты для Диспетчера рассылки уведомлений во внешние сервисы."""

import sys
import asyncio
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.core.database import init_db, get_db_connection
from backend.core.alerting import _should_send, PROVIDERS, send_alert
from backend.api.alerting import create_channel, get_channels, delete_channel, AlertChannelPayload


async def run_dispatcher_tests():
    init_db()

    # 1. Проверка логики фильтрации по уровням критичности _should_send
    assert _should_send(min_type="warning", notif_type="error", categories="*", notif_cat="system") is True
    assert _should_send(min_type="warning", notif_type="info", categories="*", notif_cat="system") is False
    assert _should_send(min_type="error", notif_type="error", categories="stream,tuya", notif_cat="tuya") is True
    assert _should_send(min_type="error", notif_type="error", categories="stream,tuya", notif_cat="system") is False

    # 2. Проверка наличия всех задекларированных провайдеров
    for provider_name in ["telegram", "discord", "viber", "email", "webhook", "syslog"]:
        assert provider_name in PROVIDERS

    # 3. Тест создания канала алертинга через API модель
    payload = AlertChannelPayload(
        name="Тестовый Telegram",
        type="telegram",
        enabled=True,
        min_type="warning",
        categories="*",
        config={"bot_token": "mock_token", "chat_id": "mock_chat"},
    )
    res = await create_channel(payload)
    assert res["status"] == "ok"
    integration_id = res["id"]

    # 4. Получение списка каналов
    items = await get_channels()
    assert any(i["id"] == integration_id for i in items)

    # 5. Тест выполнения алертинга (без реальной отправки в внешнюю сеть)
    sync_res = send_alert(
        title="Тест сбоя",
        message="Потеря связи с устройством",
        severity="error",
        category="system"
    )
    assert integration_id in sync_res

    # 6. Удаление канала
    del_res = await delete_channel(integration_id)
    assert del_res["status"] == "ok"

    print("Notification Alerting tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_dispatcher_tests())
