import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.auth import create_ws_ticket, consume_ws_ticket

client = TestClient(app)

def test_ws_ticket_generation_and_consumption():
    """Тест создания и одноразового погашения тикета WebSocket."""
    ticket = create_ws_ticket(user_id="42", jti="test-jti-123")
    assert ticket.startswith("wst_")
    
    consumed = consume_ws_ticket(ticket)
    assert consumed is not None
    assert str(consumed["user_id"]) == "42"
    assert consumed.get("jti") == "test-jti-123"

    # Повторное погашение одноразового билета должно возвращать None
    assert consume_ws_ticket(ticket) is None


def test_ws_connection_auth_disabled_anonymous_user_id(monkeypatch):
    """При auth_enabled=False подключение без токена должно получать user_id=None, а не '1'."""
    monkeypatch.setenv("NMS_DISABLE_AUTH", "1")

    with client.websocket_connect("/api/events/ws") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert "pong" in data


def test_ws_frame_size_limit(monkeypatch):
    """Превышение MAX_FRAME_SIZE (64KB) приводит к закрытию соединения с кодом 1009."""
    monkeypatch.setenv("NMS_DISABLE_AUTH", "1")

    with client.websocket_connect("/api/events/ws") as websocket:
        oversized_payload = "A" * (65536 + 100)
        websocket.send_text(oversized_payload)
        with pytest.raises(Exception):
            websocket.receive_text()

