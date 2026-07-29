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

    # 10. Проверка экспорта логов аудита в CSV
    export_res = client.get("/api/audit-logs/export", headers=headers)
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]
    assert "audit_logs.csv" in export_res.headers["content-disposition"]

    # 11. Проверка получения и сохранения настроек безопасности
    sec_get_res = client.get("/api/settings/security", headers=headers)
    assert sec_get_res.status_code == 200
    sec_data = sec_get_res.json()
    assert "auth_enabled" in sec_data

    sec_put_res = client.put(
        "/api/settings/security",
        json={
            "auth_enabled": True,
            "mandatory_password_change": True,
            "max_login_attempts": 7,
            "lockout_duration": 45,
        },
        headers=headers,
    )
    assert sec_put_res.status_code == 200

    sec_updated_res = client.get("/api/settings/security", headers=headers)
    assert sec_updated_res.json()["max_login_attempts"] == 7
    assert sec_updated_res.json()["lockout_duration"] == 45

