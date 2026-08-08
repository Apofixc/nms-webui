"""Модульные и интеграционные тесты для 5 фич системы алертинга."""

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
    _should_send,
    _format_message_with_template,
    _make_http_post,
    calculate_fingerprint,
    should_deduplicate,
    reset_dedup_cache,
    is_in_maintenance,
    process_unacked_escalations,
    send_alert,
    PROVIDERS,
)
from backend.api.alerting import (
    create_channel,
    get_channels,
    delete_channel,
    AlertChannelPayload,
    create_maintenance_window,
    get_maintenance_windows,
    delete_maintenance_window,
    MaintenanceWindowPayload,
    create_escalation_rule,
    get_escalation_rules,
    delete_escalation_rule,
    EscalationRulePayload,
)


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    reset_dedup_cache()
    yield
    reset_dedup_cache()


def test_should_send_filtering():
    """Тест фильтрации по минимальной критичности и категории."""
    assert _should_send(min_type="warning", notif_type="error", categories="*", notif_cat="system") is True
    assert _should_send(min_type="warning", notif_type="info", categories="*", notif_cat="system") is False
    assert _should_send(min_type="error", notif_type="error", categories="stream,tuya", notif_cat="tuya") is True
    assert _should_send(min_type="error", notif_type="error", categories="stream,tuya", notif_cat="system") is False


def test_deduplication_cache():
    """Тест 1: Проверка работы алгоритма дедупликации (Fingerprint + Cache)."""
    fp = calculate_fingerprint("Потеря соединения", "network", "error")
    
    is_dedup1, count1 = should_deduplicate(fp, window_sec=60)
    assert is_dedup1 is False
    assert count1 == 1

    is_dedup2, count2 = should_deduplicate(fp, window_sec=60)
    assert is_dedup2 is True
    assert count2 == 2


def test_template_formatting():
    """Тест 5: Проверка форматирования сообщений по кастомным шаблонам."""
    config = {
        "template": "ALERT: [{severity}] {title} - {message} (Category: {category})"
    }
    raw_alert = {
        "title": "Сбой питания",
        "message": "UPS 1 разряжен",
        "severity": "critical",
        "category": "power",
    }
    res = _format_message_with_template(config, raw_alert)
    assert res["message"] == "ALERT: [critical] Сбой питания - UPS 1 разряжен (Category: power)"


def test_maintenance_windows():
    """Тест 3: Проверка подавления алертов во время окна обслуживания."""
    conn = get_db_connection()
    now = datetime.now()
    starts = (now - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    ends = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

    with conn:
        conn.execute("DELETE FROM maintenance_windows")
        conn.execute(
            """
            INSERT INTO maintenance_windows (id, name, target_category, starts_at, ends_at, enabled)
            VALUES ('maint-1', 'Профилактика сети', 'network', ?, ?, 1)
            """,
            (starts, ends),
        )
    conn.close()

    assert is_in_maintenance("network") is True
    assert is_in_maintenance("database") is False


@pytest.mark.asyncio
async def test_escalation_rules():
    """Тест 4: Проверка эскалации неквитированных алертов."""
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM notifications")
        conn.execute("DELETE FROM alert_channels")
        conn.execute("DELETE FROM escalation_rules")

        conn.execute(
            """
            INSERT INTO alert_channels (id, name, type, enabled, config)
            VALUES ('chan-esc', 'Escalation Channel', 'webhook', 1, '{"webhook_url": "http://localhost/mock"}')
            """
        )
        conn.execute(
            """
            INSERT INTO escalation_rules (id, name, min_severity, unack_timeout_sec, target_channel_id, enabled)
            VALUES ('esc-1', 'Эскалация ошибок', 'error', 0, 'chan-esc', 1)
            """
        )
        old_time = (datetime.now() - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            INSERT INTO notifications (title, message, type, category, read, acknowledged, created_at, escalated)
            VALUES ('Критический сбой', 'Сервер не отвечает', 'error', 'system', 0, 0, ?, 0)
            """,
            (old_time,),
        )
    conn.close()

    escalated = process_unacked_escalations()
    assert escalated == 1

    conn = get_db_connection()
    row = conn.execute("SELECT escalated FROM notifications WHERE title = 'Критический сбой'").fetchone()
    assert row["escalated"] == 1
    conn.close()


@pytest.mark.asyncio
async def test_alerting_api_integration():
    """Тест 2 & REST API: Интеграционный тест каналов, техобслуживания и эскалаций."""
    # 1. Канал
    c_res = await create_channel(AlertChannelPayload(
        name="Test Telegram",
        type="telegram",
        enabled=True,
        min_type="warning",
        categories="*",
        config={"bot_token": "token123", "chat_id": "12345"},
    ))
    assert c_res["status"] == "ok"
    c_id = c_res["id"]

    channels = await get_channels()
    assert any(c["id"] == c_id for c in channels)

    # 2. Окно обслуживания
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    m_res = await create_maintenance_window(MaintenanceWindowPayload(
        name="Техработы",
        target_category="system",
        starts_at=now,
        ends_at=now,
        enabled=True
    ))
    assert m_res["status"] == "ok"
    m_id = m_res["id"]

    maints = await get_maintenance_windows()
    assert any(m["id"] == m_id for m in maints)

    # 3. Правило эскалации
    e_res = await create_escalation_rule(EscalationRulePayload(
        name="Эскалация",
        min_severity="error",
        unack_timeout_sec=300,
        target_channel_id=c_id,
        enabled=True
    ))
    assert e_res["status"] == "ok"
    e_id = e_res["id"]

    escs = await get_escalation_rules()
    assert any(e["id"] == e_id for e in escs)

    # Зачистка
    await delete_channel(c_id)
    await delete_maintenance_window(m_id)
    await delete_escalation_rule(e_id)
