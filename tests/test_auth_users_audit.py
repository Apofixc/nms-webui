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
    assert "Нельзя отключить" in lock_res.json()["detail"] or "Cannot disable" in lock_res.json()["detail"]

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
    headers = {"Authorization": f"Bearer {relog_res.json()['token']}"}

    # 9. Проверка логов аудита
    audit_res = client.get("/api/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["total"] >= 1

    # 10. Проверка экспорта логов аудита в CSV
    export_res = client.get("/api/audit-logs/export?format=csv", headers=headers)
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


def test_login_rate_limiting_lockout(client: TestClient):
    login_res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Настраиваем макс. попыток входа = 3
    client.put(
        "/api/settings/security",
        json={"auth_enabled": True, "mandatory_password_change": False, "max_login_attempts": 3, "lockout_duration": 15},
        headers=headers,
    )

    # 1 и 2 неверные попытки -> 401
    assert client.post("/api/auth/login", json={"username": "root", "password": "wrong1"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "root", "password": "wrong2"}).status_code == 401

    # 3 неверная попытка -> достигнут лимит 3, происходит блокировка -> 429
    res3 = client.post("/api/auth/login", json={"username": "root", "password": "wrong3"})
    assert res3.status_code == 429

    # Последующая попытка до истечения срока блокировки -> 429
    res4 = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    assert res4.status_code == 429


def test_must_change_password_flow(client: TestClient):
    login_res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создаем пользователя с обязательной сменой пароля
    create_res = client.post(
        "/api/users",
        json={
            "username": "new_operator",
            "password": "TempPassword123!",
            "full_name": "Новый Оператор",
            "email": "operator@nms.local",
            "uid": "OP-999",
            "role_id": "3",
            "is_active": True,
            "must_change_password": True,
        },
        headers=headers,
    )
    assert create_res.status_code == 200

    # Вход под новым пользователем
    op_login = client.post("/api/auth/login", json={"username": "new_operator", "password": "TempPassword123!"})
    assert op_login.status_code == 200
    op_data = op_login.json()
    assert op_data["must_change_password"] is True

    op_token = op_data["token"]
    op_headers = {"Authorization": f"Bearer {op_token}"}

    # Смена пароля
    chg_res = client.put(
        "/api/users/me/password",
        json={"old_password": "TempPassword123!", "new_password": "NewStrongPassword456!"},
        headers=op_headers,
    )
    assert chg_res.status_code == 200

    # Повторный вход со новым паролем
    new_login = client.post("/api/auth/login", json={"username": "new_operator", "password": "NewStrongPassword456!"})
    assert new_login.status_code == 200
    assert new_login.json()["must_change_password"] is False


def test_auth_bypass_mode(client: TestClient):
    login_res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Выключаем системную авторизацию (auth_enabled = False)
    client.put(
        "/api/settings/security",
        json={"auth_enabled": False, "mandatory_password_change": False, "max_login_attempts": 5, "lockout_duration": 30},
        headers=headers,
    )

    # Без заголовка Authorization запрос должен успешно проходить под root
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "root"


def test_rbac_permissions_enforcement(client: TestClient):
    # 1. Вход под root
    login_res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    token = login_res.json()["token"]
    root_headers = {"Authorization": f"Bearer {token}"}

    # 2. Создаем пользователя с ролью Viewer (role_id = '4')
    create_res = client.post(
        "/api/users",
        json={
            "username": "viewer_user",
            "password": "Password123!",
            "full_name": "Тестовый Viewer",
            "email": "viewer@nms.local",
            "uid": "VIEWER-001",
            "role_id": "4",
            "is_active": True,
        },
        headers=root_headers,
    )
    assert create_res.status_code == 200

    # 3. Авторизуемся под Viewer
    v_login = client.post("/api/auth/login", json={"username": "viewer_user", "password": "Password123!"})
    assert v_login.status_code == 200
    v_token = v_login.json()["token"]
    v_headers = {"Authorization": f"Bearer {v_token}"}

    # 4. Viewer НЕ имеет доступа на чтение списка пользователей (users.view) -> 403 Forbidden
    get_users_res = client.get("/api/users", headers=v_headers)
    assert get_users_res.status_code == 403

    # 5. Viewer не имеет доступа на создание пользователей (users.manage) -> 403 Forbidden
    create_forbidden = client.post(
        "/api/users",
        json={
            "username": "illegal_user",
            "password": "Password123!",
            "full_name": "Hacker",
            "role_id": "4",
        },
        headers=v_headers,
    )
    assert create_forbidden.status_code == 403

    # 6. Viewer не имеет доступа к созданию/редактированию ролей (roles.manage) -> 403 Forbidden
    role_forbidden = client.post(
        "/api/roles",
        json={"name": "Illegal Role", "description": "Hacked", "permission_ids": []},
        headers=v_headers,
    )
    assert role_forbidden.status_code == 403

    # 7. Viewer не имеет доступа к администрированию системы (system.admin) -> 403 Forbidden
    sys_forbidden = client.get("/api/system/backup", headers=v_headers)
    assert sys_forbidden.status_code == 403


def test_force_mfa_flow(client: TestClient):
    from backend.core.mfa import get_totp_code

    login_res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Включаем force_mfa
    client.put(
        "/api/settings/security",
        json={"auth_enabled": True, "mandatory_password_change": False, "max_login_attempts": 5, "lockout_duration": 30, "force_mfa": True},
        headers=headers,
    )

    # 2. Создаем нового пользователя без 2FA
    client.post(
        "/api/users",
        json={
            "username": "mfa_target_user",
            "password": "Password123!",
            "full_name": "Пользователь MFA",
            "email": "mfa@nms.local",
            "role_id": "3",
            "is_active": True,
        },
        headers=headers,
    )

    # 3. Логин под mfa_target_user при force_mfa == True
    mfa_login = client.post("/api/auth/login", json={"username": "mfa_target_user", "password": "Password123!"})
    assert mfa_login.status_code == 200
    mfa_data = mfa_login.json()
    assert mfa_data["mfa_required"] is True
    assert mfa_data["mfa_setup_required"] is True
    assert mfa_data["mfa_ticket"] is not None
    assert mfa_data["qr_code"] is not None
    secret = mfa_data["secret"]
    ticket = mfa_data["mfa_ticket"]
    assert secret is not None

    # 4. Неверный код -> 401
    bad_verify = client.post("/api/auth/mfa/verify", json={"mfa_ticket": ticket, "code": "000000"})
    assert bad_verify.status_code == 401

    # 5. Верный TOTP код -> успешный вход + активация 2FA
    valid_code = get_totp_code(secret)
    good_verify = client.post("/api/auth/mfa/verify", json={"mfa_ticket": ticket, "code": valid_code})
    assert good_verify.status_code == 200
    user_token = good_verify.json()["token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 6. Проверяем /api/auth/me -> mfa_enabled == True, force_mfa == True
    me_res = client.get("/api/auth/me", headers=user_headers)
    assert me_res.status_code == 200
    assert me_res.json()["mfa_enabled"] is True
    assert me_res.json()["force_mfa"] is True

    # 7. Попытка отключить 2FA при force_mfa == True -> 400 Bad Request
    disable_res = client.post("/api/auth/mfa/disable", headers=user_headers)
    assert disable_res.status_code == 400
    assert "запрещено политикой безопасности" in disable_res.json()["detail"] or "prohibited by system security policy" in disable_res.json()["detail"]


def test_update_own_profile_avatar(client: TestClient):
    login_res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update profile avatar via PUT /api/users/me
    avatar_data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    update_res = client.put("/api/users/me", json={"avatar": avatar_data_url}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json() == {"ok": True}

    # 2. Verify avatar persisted in /api/auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["avatar"] == avatar_data_url

    # 3. Reset avatar
    reset_res = client.put("/api/users/me", json={"avatar": ""}, headers=headers)
    assert reset_res.status_code == 200
    me_res2 = client.get("/api/auth/me", headers=headers)
    assert me_res2.json()["avatar"] == ""




