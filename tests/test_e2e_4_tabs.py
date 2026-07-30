import io
import pytest
from fastapi.testclient import TestClient
from backend.core.app import create_app
import backend.core.database as db_module

@pytest.fixture(scope="function")
def client(tmp_path):
    test_db = tmp_path / "test_nms_e2e.db"
    db_module.DB_PATH = test_db
    db_module.init_db()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

def get_admin_headers(client):
    res = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}

# ============================================================================
# 1. 🔐 Вкладка: Доступ и Идентификация (/settings)
# ============================================================================

def test_tab1_access_identity_policies(client):
    headers = get_admin_headers(client)
    
    # 1. Получение существующих настроек безопасности
    res = client.get("/api/settings/security", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)

    # 2. Сохранение обновленных параметров безопасности
    new_settings = {
        "auth_enabled": True,
        "mandatory_password_change": False,
        "force_mfa": False,
        "max_login_attempts": 5,
        "lockout_duration_mins": 15,
        "session_ttl_hours": 24,
        "inactivity_timeout_mins": 30,
        "min_password_length": 8,
        "require_uppercase": True,
        "require_numbers": True,
        "require_special": False
    }
    res_save = client.put("/api/settings/security", json=new_settings, headers=headers)
    assert res_save.status_code in (200, 201, 204)

def test_tab1_export_audit_logs(client):
    headers = get_admin_headers(client)
    res = client.get("/api/audit/logs", headers=headers)
    assert res.status_code in (200, 404)

# ============================================================================
# 2. 👥 Вкладка: Управление пользователями (/settings/users)
# ============================================================================

def test_tab2_users_management_crud(client):
    headers = get_admin_headers(client)

    # 1. Получение списка пользователей
    res = client.get("/api/users", headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    users = res_data.get("items", res_data) if isinstance(res_data, dict) else res_data
    assert isinstance(users, list)
    assert any(u["username"] == "root" for u in users)

    # 2. Создание нового пользователя
    new_user_data = {
        "username": "mcp_e2e_testuser",
        "full_name": "MCP E2E Test User",
        "email": "mcp_e2e@example.com",
        "password": "Password123!",
        "role_id": "3"
    }
    res_create = client.post("/api/users", json=new_user_data, headers=headers)
    assert res_create.status_code in (200, 201)
    user_id = res_create.json()["id"]

    # 3. Обновление пользователя
    res_update = client.put(f"/api/users/{user_id}", json={"full_name": "Updated Name"}, headers=headers)
    assert res_update.status_code == 200

    # 4. Удаление пользователя
    res_delete = client.delete(f"/api/users/{user_id}", headers=headers)
    assert res_delete.status_code in (200, 204)

def test_tab2_prevent_self_deletion(client):
    headers = get_admin_headers(client)
    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.status_code == 200
    my_id = res_me.json()["id"]

    # Попытка удалить самого себя (root)
    res_del_self = client.delete(f"/api/users/{my_id}", headers=headers)
    assert res_del_self.status_code in (400, 403, 422)

# ============================================================================
# 3. ⚙️ Вкладка: Системное администрирование (/settings/system)
# ============================================================================

def test_tab3_system_admin_logs_and_sessions(client):
    headers = get_admin_headers(client)

    # 1. Просмотр системных сессий
    res_sessions = client.get("/api/users/me/sessions", headers=headers)
    assert res_sessions.status_code == 200
    sessions_list = res_sessions.json()
    assert isinstance(sessions_list, list)

    # 2. Статус системы (список сессий)
    res_status = client.get("/api/system/sessions", headers=headers)
    assert res_status.status_code == 200

# ============================================================================
# 4. 👤 Вкладка: Профиль пользователя (/settings/profile)
# ============================================================================

def test_tab4_user_profile_avatar_and_timezone(client):
    headers = get_admin_headers(client)

    # 1. Получение информации профиля
    res_profile = client.get("/api/auth/me", headers=headers)
    assert res_profile.status_code == 200

    # 2. Обновление часового пояса и отображаемого имени
    update_profile = {
        "full_name": "Администратор Системы",
        "timezone": "Asia/Tokyo"
    }
    res_update = client.put("/api/users/me", json=update_profile, headers=headers)
    assert res_update.status_code == 200

    # 3. Обновление аватара через профиль
    res_avatar = client.put("/api/users/me", json={"avatar": "data:image/png;base64,iVBORw0KGgo="}, headers=headers)
    assert res_avatar.status_code == 200

    # 4. Список собственных сессий
    res_my_sessions = client.get("/api/users/me/sessions", headers=headers)
    assert res_my_sessions.status_code == 200
    my_sessions = res_my_sessions.json()
    assert isinstance(my_sessions, list)
    assert len(my_sessions) >= 1
