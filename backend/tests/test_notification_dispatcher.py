"""Интеграционные тесты для Диспетчера рассылки уведомлений во внешние сервисы."""

import asyncio
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.core.database import init_db
from backend.core.notification_dispatcher import PROVIDERS, _should_send, dispatch_notification_sync
from backend.core.notifications_api import IntegrationPayload, create_integration, delete_integration, get_integrations


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

    # 3. Тест создания интеграции через API модель
    payload = IntegrationPayload(
        name="Тестовый Telegram",
        type="telegram",
        enabled=True,
        min_type="warning",
        categories="*",
        config={"bot_token": "mock_token", "chat_id": "mock_chat"},
    )
    res = await create_integration(payload)
    assert res["status"] == "ok"
    integration_id = res["id"]

    # 4. Получение списка интеграций
    items = await get_integrations()
    assert any(i["id"] == integration_id for i in items)

    # 5. Тест выполнения диспетчеризации (без реальной отправки в внешнюю сеть)
    sync_res = dispatch_notification_sync({
        "id": 100,
        "title": "Тест сбоя",
        "message": "Потеря связи с устройством",
        "type": "error",
        "category": "system"
    })
    assert integration_id in sync_res

    # 6. Удаление интеграции
    del_res = await delete_integration(integration_id)
    assert del_res["status"] == "ok"

    print("Notification Dispatcher tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_dispatcher_tests())
