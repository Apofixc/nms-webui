"""Integration tests for Auth, Users, Roles, Audit Logs and Root Lockout Protection."""
import pytest
from fastapi.testclient import TestClient

from backend.core.app import create_app
from backend.core.database import init_db
from backend.scripts.reset_root import reset_root_account


import backend.core.database as db_module

@pytest.fixture(scope="function")
def client(tmp_path):
    test_db = tmp_path / "test_nms.db"
    db_module.DB_PATH = test_db
    db_module.init_db()
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_login_and_auth_flow(client: TestClient):
    # 1. Попытка входа с неверным паролем
    bad_res = client.post("/api/auth/login", json={"username": "root", "password": "wrongpassword"})
    assert bad_res.status_code == 401

    # 2. Успешный вход root / admin
    login_res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    assert login_res.status_code == 200
    data = login_res.json()
    assert "token" in data
    token = data["token"]
    assert data["user"]["username"] == "root"

    # 3. Запрос профиля с токеном
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "root"

    # 4. Попытка деактивировать root когда нет других суперадминов -> 400 Bad Request
    root_id = me_res.json()["id"]
    lock_res = client.put(f"/api/users/{root_id}", json={"is_active": False}, headers=headers)
    assert lock_res.status_code == 400
    assert "Нельзя отключить" in lock_res.json()["detail"]

    # 5. Создаем второго суперадмина
    create_res = client.post(
        "/api/users",
        json={
            "username": "alt_superuser",
            "password": "Password123!",
            "full_name": "Второй суперадмин",
            "email": "alt@nms.local",
            "uid": "ALT-001",
            "role_id": "1",
            "is_active": True,
        },
        headers=headers,
    )
    assert create_res.status_code == 200

    # 6. Теперь деактивация root разрешается
    lock_ok_res = client.put(f"/api/users/{root_id}", json={"is_active": False}, headers=headers)
    assert lock_ok_res.status_code == 200

    # 7. Тестирование CLI реанимации
    assert reset_root_account() is True

    # 8. Проверка входа root после реанимации
    relog_res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    assert relog_res.status_code == 200

    # 9. Проверка логов аудита
    audit_res = client.get("/api/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["total"] >= 1
