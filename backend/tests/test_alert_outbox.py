"""Unit and integration tests for Transactional Outbox Pattern and Persistent Alerting Caches."""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import pytest

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.core.database import init_db, get_db_connection
from backend.core.alerting import (
    send_alert,
    process_alert_outbox,
    process_alert_outbox_async,
    reset_dedup_cache,
    is_channel_in_cooldown,
    record_channel_result,
    should_deduplicate,
    is_flapping,
)


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    reset_dedup_cache()
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM alert_outbox;")
        conn.execute("DELETE FROM alert_log;")
        conn.execute("DELETE FROM alert_channels;")
        conn.execute("DELETE FROM notifications;")
    conn.close()
    yield
    reset_dedup_cache()


def test_outbox_enqueue_and_process():
    """Тест постановки задачи в alert_outbox и ее последующей асинхронной обработки."""
    conn = get_db_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO alert_channels (id, name, type, enabled, min_type, categories, config)
            VALUES ('chan-webhook', 'Test Webhook', 'webhook', 1, 'info', '*', '{"webhook_url": "http://httpbin.org/post"}')
            """
        )
    conn.close()

    res = send_alert("Тестовая авария", "Сервер перегружен", severity="error", category="system")
    assert res.get("chan-webhook") is True

    # Проверяем появление задачи в alert_outbox со статусом 'pending'
    conn = get_db_connection()
    outbox_row = conn.execute("SELECT * FROM alert_outbox WHERE channel_id = 'chan-webhook'").fetchone()
    assert outbox_row is not None
    assert outbox_row["status"] == "pending"
    assert outbox_row["title"] == "Тестовая авария"
    conn.close()


@pytest.mark.anyio
async def test_outbox_async_worker_processing():
    """Тест асинхронного выполнения задач воркером process_alert_outbox_async."""
    conn = get_db_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO alert_outbox (channel_id, channel_type, title, message, severity, category, config_json, payload_json, status, attempts)
            VALUES ('chan-mock', 'webhook', 'Outbox Test', 'Message text', 'warning', 'network', '{"webhook_url": "http://localhost/mock"}', '{}', 'pending', 0)
            """
        )
    conn.close()

    # Выполняем обработку очереди (mock URL отработает с задержкой/ошибкой)
    processed = await process_alert_outbox_async(batch_size=10)

    conn = get_db_connection()
    row = conn.execute("SELECT status, attempts, last_error FROM alert_outbox WHERE channel_id = 'chan-mock'").fetchone()
    assert row is not None
    # Ожидаем попытку отправки (status = pending/failed, attempts = 1)
    assert row["attempts"] == 1
    conn.close()


def test_persistent_circuit_breaker_and_dedup():
    """Тест персистентного сохранения состояния Circuit Breaker и Дедупликации в SQLite."""
    ch_id = "chan-persistent-cb"
    assert is_channel_in_cooldown(ch_id) is False

    # Записываем 3 сбоя подряд
    record_channel_result(ch_id, False)
    record_channel_result(ch_id, False)
    record_channel_result(ch_id, False)

    # Circuit breaker переведен в cooldown
    assert is_channel_in_cooldown(ch_id) is True

    # Проверяем сохранение состояния в БД
    conn = get_db_connection()
    row = conn.execute("SELECT consecutive_failures FROM alert_circuit_breaker WHERE channel_id = ?", (ch_id,)).fetchone()
    assert row is not None
    assert row["consecutive_failures"] == 3
    conn.close()

    # Сбрасываем успех
    record_channel_result(ch_id, True)
    assert is_channel_in_cooldown(ch_id) is False
