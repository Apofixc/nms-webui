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


def test_ws_log_stream_auth_rejection():
    """Тест отклонения анонимного стриминга логов без токена."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/api/system/logs/backend.log/stream"):
            pass


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
