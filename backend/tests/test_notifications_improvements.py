import time
import json
from backend.core.database import init_db, get_db_connection
from backend.core.notify import (
    notify,
    process_alert_escalations,
    export_user_notifications,
    get_user_notifications,
)


def test_smart_summarization_title_template():
    """Тест умной группировки с title_template (динамическое обновление шаблона)."""
    init_db()
    user_id = "test_template_user"

    # 1. Первое событие с title_template
    res1 = notify(
        user_id=user_id,
        title="Потеряно соединение с 1 устройством",
        title_template="Потеряно соединение с {count} устройствами",
        severity="warning",
        module_id="devices",
    )
    assert res1 is not None
    assert res1["group_count"] == 1
    assert res1["title"] == "Потеряно соединение с 1 устройствами"

    # 2. Повторное событие в интервале дедупликации (60 сек)
    res2 = notify(
        user_id=user_id,
        title="Потеряно соединение с 1 устройством",
        title_template="Потеряно соединение с {count} устройствами",
        severity="warning",
        module_id="devices",
    )
    assert res2 is not None
    assert res2["group_count"] == 2
    assert res2["title"] == "Потеряно соединение с 2 устройствами"

    # Проверка получения в списке
    items = get_user_notifications(user_id=user_id)["items"]
    assert len(items) == 1
    assert items[0]["group_count"] == 2
    assert items[0]["title"] == "Потеряно соединение с 2 устройствами"


def test_alert_escalation_flow():
    """Тест эскалации неквитированных и непрочитанных алертов со статусом error."""
    init_db()
    user_id = "test_escalation_user"

    # Создаем тестовую ошибку напрямую со старым созданием (30 минут назад)
    old_ts = time.time() - 1800.0
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO notifications (module_id, user_id, title, body, severity, category, created_at, read_at, acknowledged_at, escalated_at)
                VALUES ('core', ?, 'Критический сбой сервера', 'Сбой системы питания', 'error', 'system', ?, NULL, NULL, NULL)
                """,
                (user_id, old_ts),
            )
    finally:
        conn.close()

    # Запускаем обработку эскалаций (порог 15 минут)
    escalated_count = process_alert_escalations(escalation_minutes=15)
    assert escalated_count >= 1

    # Проверяем, что у уведомления выставилось escalated_at
    notifs = get_user_notifications(user_id=user_id)["items"]
    escalated_item = next((i for i in notifs if i["title"] == "Критический сбой сервера"), None)
    assert escalated_item is not None
    assert escalated_item["escalated_at"] is not None
    assert isinstance(escalated_item["escalated_at"], float)


def test_export_user_notifications():
    """Тест выгрузки лога уведомлений в форматах CSV и JSON."""
    init_db()
    user_id = "test_export_user"

    notify(
        user_id=user_id,
        title="Тестовый экспорт 1",
        body="Детали 1",
        severity="info",
    )
    notify(
        user_id=user_id,
        title="Тестовый экспорт 2",
        body="Детали 2",
        severity="error",
    )

    # 1. Экспорт в CSV
    csv_content, csv_mime = export_user_notifications(user_id=user_id, export_format="csv")
    assert csv_mime == "text/csv"
    assert "ID,Module,Title,Body,Severity" in csv_content
    assert "Тестовый экспорт 1" in csv_content
    assert "Тестовый экспорт 2" in csv_content

    # 2. Экспорт в JSON
    json_content, json_mime = export_user_notifications(user_id=user_id, export_format="json")
    assert json_mime == "application/json"
    parsed = json.loads(json_content)
    assert isinstance(parsed, list)
    assert len(parsed) >= 2
    assert any(i["title"] == "Тестовый экспорт 1" for i in parsed)
