import pytest
from fastapi.testclient import TestClient
from backend.core.app import create_app
import backend.core.database as db_module
from backend.core.log_providers import log_provider_registry

@pytest.fixture(scope="function")
def client(tmp_path):
    test_db = tmp_path / "test_remote_sources.db"
    db_module.DB_PATH = test_db
    db_module.init_db()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

def get_admin_headers(client):
    res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    assert res.status_code == 200
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}

def test_remote_log_sources_crud(client):
    """Тестирование CRUD эндпоинтов для удаленных серверов логов."""
    headers = get_admin_headers(client)

    # 1. Список источников (изначально пуст)
    res_list = client.get("/api/system/logs/remote-sources/list", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json() == []

    # 2. Добавление удаленного сервера логов
    payload = {
        "name": "Node-Alpha",
        "url": "http://192.168.1.50:9000/api/system/logs/backend.log",
        "api_token": "secret_token_123"
    }
    res_add = client.post("/api/system/logs/remote-sources", json=payload, headers=headers)
    assert res_add.status_code == 200
    data_add = res_add.json()
    assert "id" in data_add
    source_id = data_add["id"]
    assert data_add["name"] == "Node-Alpha"

    # 3. Проверяем, что провайдер зарегистрирован в реестре
    provider = log_provider_registry.get(source_id)
    assert provider is not None
    assert provider.name == "Node-Alpha"

    # 4. Проверяем в общем списке системных логов
    res_logs = client.get("/api/system/logs", headers=headers)
    assert res_logs.status_code == 200
    all_logs = res_logs.json()
    assert any(l["id"] == source_id for l in all_logs)

    # 5. Удаление источника
    res_del = client.delete(f"/api/system/logs/remote-sources/{source_id}", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json()["ok"] is True

    # 6. Проверяем, что отрегистрирован
    assert log_provider_registry.get(source_id) is None


def test_websocket_log_stream_endpoint(client):
    """Тестирование эндпоинта WebSocket-стриминга логов."""
    with client.websocket_connect("/api/system/logs/backend.log/stream?level=ALL") as websocket:
        data = websocket.receive_json()
        assert "id" in data
        assert "content" in data
        assert isinstance(data["content"], list)
