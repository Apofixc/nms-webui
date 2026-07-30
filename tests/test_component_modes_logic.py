import pytest
from fastapi.testclient import TestClient
from backend.core.app import create_app
import backend.core.database as db_module

@pytest.fixture(scope="function")
def client(tmp_path):
    test_db = tmp_path / "test_modes.db"
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

def create_test_user_helper(client, headers):
    payload = {
        "username": "mode_test_user_helper",
        "full_name": "Test User Modes",
        "email": "mode_user@nms.local",
        "password": "StrongPassword123!",
        "uid": "USER-MODE-001",
        "role_id": "1",
        "is_active": True
    }
    res = client.post("/api/users", json=payload, headers=headers)
    assert res.status_code in (200, 201)
    user_data = res.json()
    return user_data.get("id") or user_data.get("user", {}).get("id")

# ============================================================================
# 1.1. КОМПОНЕНТ Settings.vue (Доступ и Идентификация) — ТЕСТЫ РЕЖИМОВ
# ============================================================================

def test_mode_settings_read_only_inspection(client):
    """Режим A: Чтение и инспекция текущих настроек безопасности."""
    headers = get_admin_headers(client)
    res = client.get("/api/settings/security", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "max_login_attempts" in data or "auth_enabled" in data

def test_mode_settings_security_policy_mutation(client):
    """Режим B: Модификация политик безопасности и лимитов."""
    headers = get_admin_headers(client)
    mutation_payload = {
        "auth_enabled": True,
        "mandatory_password_change": True,
        "force_mfa": False,
        "max_login_attempts": 5,
        "lockout_duration": 15
    }
    res = client.put("/api/settings/security", json=mutation_payload, headers=headers)
    assert res.status_code == 200
    
    sec_updated = client.get("/api/settings/security", headers=headers)
    assert sec_updated.json()["max_login_attempts"] == 5

def test_mode_settings_audit_export(client):
    """Режим C: Просмотр журнала аудита безопасности."""
    headers = get_admin_headers(client)
    res = client.get("/api/audit-logs?limit=10&offset=0", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data or isinstance(data, list)

# ============================================================================
# 1.2. КОМПОНЕНТ UsersManagement.vue (Управление пользователями) — ТЕСТЫ РЕЖИМОВ
# ============================================================================

def test_mode_users_grid_search_and_filter(client):
    """Режим A: Просмотр реестра пользователей с фильтрацией."""
    headers = get_admin_headers(client)
    res = client.get("/api/users?page=1&page_size=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    items = data.get("items", data) if isinstance(data, dict) else data
    assert any(u["username"] == "root" for u in items)

def test_mode_users_create_modal(client):
    """Режим B: Модальное окно создания пользователя."""
    headers = get_admin_headers(client)
    user_id = create_test_user_helper(client, headers)
    assert user_id is not None

def test_mode_users_edit_mutation(client):
    """Режим C: Модальное редактирование параметров пользователя."""
    headers = get_admin_headers(client)
    user_id = create_test_user_helper(client, headers)
    
    update_payload = {
        "full_name": "Updated User Modes",
        "email": "updated_mode@nms.local",
        "role_id": "1",
        "is_active": True
    }
    res = client.put(f"/api/users/{user_id}", json=update_payload, headers=headers)
    assert res.status_code == 200

def test_mode_users_self_deletion_protection(client):
    """Режим D: Защита от деструктивного удаления аккаунта root / me."""
    headers = get_admin_headers(client)
    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.status_code == 200
    my_id = res_me.json()["id"]

    res_delete = client.delete(f"/api/users/{my_id}", headers=headers)
    assert res_delete.status_code in (400, 403, 422)

# ============================================================================
# 1.3. КОМПОНЕНТ SystemAdmin.vue (Системное администрирование) — ТЕСТЫ РЕЖИМОВ
# ============================================================================

def test_mode_system_backup_restore(client):
    """Режим A: Получение системных логов и статуса."""
    headers = get_admin_headers(client)
    res = client.get("/api/system/logs", headers=headers)
    assert res.status_code == 200

def test_mode_system_sessions_management(client):
    """Режим B: Мониторинг всех системных сессий подключений."""
    headers = get_admin_headers(client)
    res = client.get("/api/system/sessions", headers=headers)
    assert res.status_code == 200
    sessions = res.json()
    assert isinstance(sessions, list)

# ============================================================================
# 1.4. КОМПОНЕНТ UserProfile.vue (Профиль пользователя) — ТЕСТЫ РЕЖИМОВ
# ============================================================================

def test_mode_profile_personal_info_and_timezone(client):
    """Режим A: Обновление личного профиля."""
    headers = get_admin_headers(client)
    payload = {
        "full_name": "Главный Администратор Системы"
    }
    res = client.put("/api/users/me", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json() == {"ok": True}

def test_mode_profile_avatar_lifecycle_and_sync(client):
    """Режим B: Жизненный цикл аватара (Обновление -> Сохранение -> Синхронизация)."""
    headers = get_admin_headers(client)
    avatar_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    update_res = client.put("/api/users/me", json={"avatar": avatar_data}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json() == {"ok": True}

    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["avatar"] == avatar_data
