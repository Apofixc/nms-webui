"""Дополнительные интеграционные тесты для подсистемы уведомлений и алертинга.

Проверяют:
1. Авто-закрытие тревог (Auto-Resolve Flow) при поступлении события с type/status="resolved" и entity_id.
2. Агрегацию и группировку сообщений в очереди alert_outbox по group_key.
3. Ограничение частоты сообщений (Rate Limiting / Token Bucket) для каналов связи.
4. Комплексную фоновую очистку БД (Retention Policy).
"""

import sys
import time
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.core.database import init_db, get_db_connection, run_full_retention_cleanup
from backend.api.notifications import create_notification
from backend.core.alerting import send_alert, check_channel_rate_limit, process_alert_outbox


def test_auto_resolve_flow():
    init_db()
    entity = "sensor:temp:room_101"

    # 1. Генерируем аварийное событие (firing)
    firing_notif = create_notification(
        title="Перегрев серверной",
        message="Температура поднялась до 85°C",
        notification_type="error",
        category="telemetry",
        entity_id=entity,
        status="firing",
    )
    assert firing_notif["id"] > 0
    assert firing_notif["status"] == "firing"

    # 2. Генерируем событие восстановления (resolved)
    resolved_notif = create_notification(
        title="Нормализация температуры",
        message="Температура в норме 22°C",
        notification_type="resolved",
        category="telemetry",
        entity_id=entity,
        status="resolved",
    )
    assert resolved_notif["id"] > 0

    # Проверяем, что исходная авария изменила статус на 'resolved'
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT status, read, message, resolved_at FROM notifications WHERE id = ?", (firing_notif["id"],)).fetchone()
        assert row["status"] == "resolved"
        assert row["read"] == 1
        assert "Восстановлено" in row["message"]
    finally:
        conn.close()


def test_outbox_grouping():
    init_db()
    conn = get_db_connection()
    try:
        # Очищаем активные окна обслуживания для корректности теста
        conn.execute("DELETE FROM maintenance_windows;")
        conn.execute("DELETE FROM alert_outbox WHERE channel_id = 'test_chan_1';")
        conn.execute("DELETE FROM alert_log WHERE channel_id = 'test_chan_1';")
        conn.commit()

        # Регистрируем тестовый активный канал
        conn.execute(
            """
            INSERT INTO alert_channels (id, name, type, enabled, min_type, categories, config, max_per_minute)
            VALUES ('test_chan_1', 'Test Channel', 'webhook', 1, 'info', '*', '{"webhook_url":"http://localhost/test"}', 30)
            ON CONFLICT(id) DO UPDATE SET enabled = 1
            """
        )
        conn.commit()

        # Отправляем 3 аперта одной категории в течение короткого окна
        send_alert(title="Сбой интерфейса 1", message="Link down 1", severity="warning", category="network", force_send=True)
        send_alert(title="Сбой интерфейса 2", message="Link down 2", severity="warning", category="network", force_send=True)
        send_alert(title="Сбой интерфейса 3", message="Link down 3", severity="warning", category="network", force_send=True)

        # В очереди outbox должна остаться 1 сгруппированная задача для этого канала
        row = conn.execute(
            "SELECT count(*) as cnt, title, payload_json FROM alert_outbox WHERE channel_id = 'test_chan_1' AND status = 'pending'"
        ).fetchone()
        assert row["cnt"] == 1
        assert "3 событий" in row["title"]
    finally:
        conn.close()


def test_channel_rate_limiting():
    init_db()
    conn = get_db_connection()
    try:
        channel_id = "test_rate_chan"
        # Заполняем журнал отправок alert_log до лимита в 3 записи за минуту
        for i in range(3):
            conn.execute(
                """
                INSERT INTO alert_log (channel_id, channel_type, title, message, severity, category, success, suppressed)
                VALUES (?, 'webhook', 'Test', 'Test', 'warning', 'system', 1, 0)
                """,
                (channel_id,),
            )
        conn.commit()

        # При лимите max_per_minute=3 проверка должна вернуть False
        assert check_channel_rate_limit(channel_id, max_per_minute=3, conn=conn) is False

        # При лимите max_per_minute=5 проверка должна вернуть True
        assert check_channel_rate_limit(channel_id, max_per_minute=5, conn=conn) is True
    finally:
        conn.close()


def test_full_retention_cleanup():
    init_db()
    # Создаем старую прочитанную запись
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO notifications (title, message, type, category, read, created_at)
            VALUES ('Старое событие', 'Устарело', 'info', 'system', 1, datetime('now', '-40 days'))
            """
        )
        conn.commit()
    finally:
        conn.close()

    res = run_full_retention_cleanup(retention_days=30)
    assert res["notifications"] >= 1


if __name__ == "__main__":
    test_auto_resolve_flow()
    test_outbox_grouping()
    test_channel_rate_limiting()
    test_full_retention_cleanup()
    print("Advanced notification tests passed successfully!")
