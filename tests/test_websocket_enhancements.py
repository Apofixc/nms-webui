import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.database import init_db, get_db_connection
from backend.core.auth import create_access_token, create_ws_ticket, consume_ws_ticket
from backend.core.events import (
    ws_manager,
    record_event_in_db,
    get_missed_events_from_db,
    prune_system_events_journal,
    broadcaster,
)


@pytest.fixture(autouse=True)
def setup_database(tmp_path):
    import backend.core.database as db_module
    db_module.DB_PATH = tmp_path / "test_ws.db"
    init_db()


def test_sqlite_event_journal_persistence_and_pruning():
    """Тест сохранения событий в SQLite журнал и прунинга по возрасту/количеству."""
    seq1 = record_event_in_db("test_event_1", json.dumps({"foo": "bar"}))
    seq2 = record_event_in_db("test_event_2", json.dumps({"baz": "qux"}))

    assert seq1 > 0
    assert seq2 > seq1

    missed = get_missed_events_from_db(seq1)
    assert len(missed) >= 1
    assert missed[0]["seq_id"] == seq2
    assert missed[0]["baz"] == "qux"

    # Тест прунинга таблицы
    prune_system_events_journal(max_age_days=0, max_rows=1)
    missed_after = get_missed_events_from_db(0)
    assert len(missed_after) <= 1


def test_ws_events_auth_rejection():
    """Тест отсечения неаутентифицированных WebSocket подключений к /api/events/ws."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/api/events/ws"):
            pass


def test_ws_events_authenticated_connect_subprotocol():
    """Тест авторизованного подключения к /api/events/ws с subprotocol bearer."""
    token = create_access_token("usr-root-01", "root")
    client = TestClient(app)
    with client.websocket_connect("/api/events/ws", subprotocols=["bearer", token]) as websocket:
        websocket.send_text("ping")
        resp = websocket.receive_json()
        assert resp.get("type") == "pong"


def test_ws_ticket_based_authentication():
    """Тест выписки и выгашивания одноразового WebSocket билета (ticket auth)."""
    ticket = create_ws_ticket(user_id="usr-root-01", jti="jti-test-123")
    assert ticket.startswith("wst_")

    client = TestClient(app)
    with client.websocket_connect(f"/api/events/ws?token={ticket}") as websocket:
        websocket.send_text("ping")
        resp = websocket.receive_json()
        assert resp.get("type") == "pong"

    # Повторное использование того же билета должно отклоняться
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/events/ws?token={ticket}"):
            pass


def test_ws_events_resume_protocol():
    """Тест возобновления пропущенных сообщений через resume handshake."""
    token = create_access_token("usr-root-01", "root")
    client = TestClient(app)

    seq_id = record_event_in_db("critical_alert", json.dumps({"msg": "Server alert"}))

    with client.websocket_connect(f"/api/events/ws?token={token}") as websocket:
        websocket.send_json({"type": "resume", "last_event_id": seq_id - 1})
        resp = websocket.receive_json()
        assert resp.get("type") == "replay"
        assert len(resp.get("events", [])) >= 1


def test_ws_events_resume_no_new_events():
    """Тест: при отсутствии новых событий (last_event_id >= max_seq) возвращается пустой replay без resync_required."""
    token = create_access_token("usr-root-01", "root")
    client = TestClient(app)

    seq_id = record_event_in_db("test_event", json.dumps({"msg": "Hello"}))

    with client.websocket_connect(f"/api/events/ws?token={token}") as websocket:
        # Передаем актуальный seq_id
        websocket.send_json({"type": "resume", "last_event_id": seq_id})
        resp = websocket.receive_json()
        assert resp.get("type") == "replay"
        assert resp.get("events") == []


def test_ws_events_resume_gap_triggers_resync():
    """Тест: при образовании разрыва (last_event_id < min_seq - 1 из-за прунинга) возвращается resync_required."""
    token = create_access_token("usr-root-01", "root")
    client = TestClient(app)

    seq1 = record_event_in_db("event_1", json.dumps({"msg": "1"}))
    seq2 = record_event_in_db("event_2", json.dumps({"msg": "2"}))
    seq3 = record_event_in_db("event_3", json.dumps({"msg": "3"}))

    # Удаляем seq1 и seq2, оставляем только seq3 (max_rows=1)
    prune_system_events_journal(max_age_days=0, max_rows=1)

    with client.websocket_connect(f"/api/events/ws?token={token}") as websocket:
        # Спрашиваем события после 0, хотя минимальный существующий равен seq3
        websocket.send_json({"type": "resume", "last_event_id": 0})
        resp = websocket.receive_json()
        assert resp.get("type") == "resync_required"


@pytest.mark.anyio
async def test_async_event_journal_queue():
    """Тест работы асинхронной очереди журнала event_journal_queue."""
    from backend.core.events import event_journal_queue, get_missed_events_from_db

    seq1 = await event_journal_queue.record_event_async("async_evt_1", json.dumps({"key": "val1"}))
    seq2 = await event_journal_queue.record_event_async("async_evt_2", json.dumps({"key": "val2"}))

    assert seq1 > 0
    assert seq2 > seq1

    missed = get_missed_events_from_db(seq1 - 1)
    assert len(missed) >= 2




def test_ws_log_stream_auth_rejection():
    """Тест отклонения анонимного стриминга логов без токена."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/api/system/logs/backend.log/stream"):
            pass


def test_ws_disabled_auth_mode():
    """Тест успешного подключения WebSocket при отключенной аутентификации (auth_enabled = False)."""
    from backend.core.plugin.registry import set_system_setting
    set_system_setting("sec_auth_enabled", False)
    try:
        client = TestClient(app)
        with client.websocket_connect("/api/events/ws", subprotocols=["bearer", "system_disabled_auth"]) as websocket:
            websocket.send_text("ping")
            resp = websocket.receive_json()
            assert resp.get("type") == "pong"
    finally:
        set_system_setting("sec_auth_enabled", True)


def test_ws_frame_size_limit():
    """Превышение MAX_FRAME_SIZE (64KB) приводит к закрытию соединения с кодом 1009."""
    from backend.core.plugin.registry import set_system_setting
    set_system_setting("sec_auth_enabled", False)
    try:
        client = TestClient(app)
        with client.websocket_connect("/api/events/ws") as websocket:
            oversized_payload = "A" * (65536 + 100)
            websocket.send_text(oversized_payload)
            with pytest.raises(Exception):
                websocket.receive_text()
    finally:
        set_system_setting("sec_auth_enabled", True)




def test_ws_cswsh_origin_rejection():
    """Тест отклонения WebSocket подключения при поддельном Origin (CSWSH)."""
    token = create_access_token("usr-root-01", "root")
    client = TestClient(app)
    headers = {"origin": "http://evil-attacker.com"}
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/events/ws?token={token}", headers=headers):
            pass


def test_ws_revoked_session_rejection():
    """Тест отклонения подключения с аннулированной сессией (is_revoked)."""
    token = create_access_token("usr-root-01", "root")
    conn = get_db_connection()
    try:
        conn.execute("UPDATE active_sessions SET is_revoked = 1 WHERE user_id = ?", ("usr-root-01",))
        conn.commit()
    finally:
        conn.close()

    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/events/ws?token={token}"):
            pass


def test_ws_metrics_endpoint():
    """Тест получения метрик WebSocket активности."""
    metrics = ws_manager.get_metrics()
    assert "active_connections" in metrics
    assert "total_sent" in metrics
    assert "total_received" in metrics
    assert "total_dropped" in metrics


def test_dynamic_secret_key_initialization():
    """Тест динамической инициализации SECRET_KEY (не "nms-secret-key-change-in-production")."""
    from backend.core.auth import SECRET_KEY
    assert SECRET_KEY != "nms-secret-key-change-in-production"
    assert len(SECRET_KEY) >= 16


def test_ws_ack_protocol():
    """Тест подтверждения доставки команд (ACK protocol)."""
    token = create_access_token("usr-root-01", "root")
    client = TestClient(app)
    with client.websocket_connect(f"/api/events/ws?token={token}") as websocket:
        websocket.send_json({"type": "cmd_reboot", "target": "switch-01", "ack_id": "ack_12345"})
        resp = websocket.receive_json()
        assert resp.get("type") == "ack"
        assert resp.get("ack_id") == "ack_12345"
        assert resp.get("status") == "received"


def test_ws_replay_topic_filtering():
    """Тест фильтрации сообщений по топикам при досылке пропущенных событий."""
    seq1 = record_event_in_db("global_alert", json.dumps({"msg": "global"}), topic=None)
    seq2 = record_event_in_db("device_update", json.dumps({"msg": "dev1"}), topic="devices")
    seq3 = record_event_in_db("log_update", json.dumps({"msg": "log1"}), topic="logs")

    # Подписчик только на топик "devices" должен слушать global_alert и device_update, но не log_update
    from backend.core.events import check_replay_status_from_db
    status, missed = check_replay_status_from_db(seq1 - 1, topics={"devices"})
    assert status == "replay"
    received_types = [m.get("type") for m in missed]
    assert "global_alert" in received_types
    assert "device_update" in received_types
    assert "log_update" not in received_types


@pytest.mark.anyio
async def test_immediate_event_journal_queue_flush():
    """Тест немедленного флаша очереди EventJournalQueue при immediate=True без задержки 500мс."""
    import time
    from backend.core.events import EventJournalQueue

    queue = EventJournalQueue(flush_interval=0.5)
    start_time = time.monotonic()
    seq_id = await queue.record_event_async("urgent_test", json.dumps({"test": 1}), immediate=True)
    elapsed = time.monotonic() - start_time

    assert seq_id > 0
    assert elapsed < 0.15, f"Immediate event latency too high: {elapsed:.3f}s"


def test_ws_topic_subscription_permissions():
    """Тест проверки прав доступа при подписке на чувствительные топики."""
    from backend.api.events import can_subscribe_to_topic

    # Обычный пользователь без системных прав
    assert can_subscribe_to_topic("usr-operator-01", "devices") is True
    assert can_subscribe_to_topic("usr-operator-01", "admin_audit") is False
    assert can_subscribe_to_topic("usr-operator-01", "logs_system") is False

    # Суперадминистратор / Пользователь с правом system.admin
    assert can_subscribe_to_topic("usr-root-01", "admin_audit") is True
    assert can_subscribe_to_topic("usr-root-01", "logs_system") is True


def test_ws_replay_overflow_triggers_resync():
    """Тест возврата resync_required при превышении лимита недополученных событий (gap > 200)."""
    from backend.core.events import check_replay_status_from_db

    first_seq = record_event_in_db("bulk_test", json.dumps({"i": 0}))
    for i in range(1, 205):
        record_event_in_db("bulk_test", json.dumps({"i": i}))

    status, missed = check_replay_status_from_db(first_seq - 1, limit=200)
    assert status == "resync_required"
    assert len(missed) == 0


def test_ws_msgpack_binary_protocol():
    """Тест подключения и обмена бинарными кадры по протоколу MsgPack."""
    import msgpack
    token = create_access_token("usr-root-01", "root")
    client = TestClient(app)
    with client.websocket_connect(f"/api/events/ws?token={token}&protocol=msgpack") as websocket:
        packed_ping = msgpack.packb({"type": "cmd_reboot", "target": "router-01", "ack_id": "msgpack_ack_1"})
        websocket.send_bytes(packed_ping)
        resp_bytes = websocket.receive_bytes()
        resp_data = msgpack.unpackb(resp_bytes, raw=False)
        assert resp_data.get("type") == "ack"
        assert resp_data.get("ack_id") == "msgpack_ack_1"
        assert resp_data.get("status") == "received"





