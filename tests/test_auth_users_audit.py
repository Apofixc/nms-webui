"""Integration tests for Auth, Users, Roles and Audit Logs."""
import pytest
from fastapi.testclient import TestClient

from backend.core.app import create_app
from backend.core.database import init_db

@pytest.fixture(scope="module")
def client():
    init_db()
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_login_and_auth_flow(client: TestClient):
    # 1. Попытка входа с неверным паролем
    bad_res = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert bad_res.status_code == 401

    # 2. Успешный вход admin / admin
    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert login_res.status_code == 200
    data = login_res.json()
    assert "token" in data
    token = data["token"]
    assert data["user"]["username"] == "admin"

    # 3. Запрос профиля с токеном
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "admin"

    # 4. Проверка защищенного эндпоинта без токена -> 401
    unauth_res = client.get("/api/users")
    assert unauth_res.status_code == 401

    # 5. Проверка списка пользователей с токеном
    users_res = client.get("/api/users", headers=headers)
    assert users_res.status_code == 200
    assert len(users_res.json()) >= 1

    # 6. Проверка логов аудита
    audit_res = client.get("/api/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["total"] >= 1
