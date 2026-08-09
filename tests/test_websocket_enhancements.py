import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.database import init_db, get_db_connection
from backend.core.auth import create_access_token
from backend.core.events import (
    ws_manager,
    record_event_in_db,
    get_missed_events_from_db,
    broadcaster,
)


@pytest.fixture(autouse=True)
def setup_database(tmp_path):
    import backend.core.database as db_module
    db_module.DB_PATH = tmp_path / "test_ws.db"
    init_db()


def test_sqlite_event_journal_persistence():
    """Тест сохранения событий в SQLite персистентный журнал и получения по last_event_id."""
    seq1 = record_event_in_db("test_event_1", json.dumps({"foo": "bar"}))
    seq2 = record_event_in_db("test_event_2", json.dumps({"baz": "qux"}))

    assert seq1 > 0
    assert seq2 > seq1

    missed = get_missed_events_from_db(seq1)
    assert len(missed) >= 1
    assert missed[0]["seq_id"] == seq2
    assert missed[0]["baz"] == "qux"


def test_ws_events_auth_rejection():
    """Тест отсечения неаутентифицированных WebSocket подключений к /api/events/ws."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/api/events/ws"):
            pass


def test_ws_events_authenticated_connect():
    """Тест авторизованного подключения к /api/events/ws с токеном."""
    token = create_access_token("usr-root-01", "root")
    client = TestClient(app)
    with client.websocket_connect(f"/api/events/ws?token={token}") as websocket:
        websocket.send_text("ping")
        resp = websocket.receive_json()
        assert resp.get("type") == "pong"


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
