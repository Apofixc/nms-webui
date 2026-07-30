import pytest
from fastapi.testclient import TestClient
from backend.core.app import create_app
import backend.core.database as db_module

@pytest.fixture(scope="function")
def client(tmp_path):
    test_db = tmp_path / "test_users_mgmt.db"
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

# ============================================================================
# ГЛУБОКИЙ НАБОР ТЕСТОВ КОМПОНЕНТА "УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ" (/settings/users)
# ============================================================================

def test_user_grid_pagination_and_search_filters(client):
    """1. Реестр пользователей: Поиск, фильтрация по ролям и пагинация."""
    headers = get_admin_headers(client)

    # 1. Поиск пользователя root по имени
    res_search = client.get("/api/users?search=root", headers=headers)
    assert res_search.status_code == 200
    data = res_search.json()
    assert data["total"] >= 1
    assert any(u["username"] == "root" for u in data["items"])

    # 2. Фильтрация по роли 1 (Administrator/Superuser)
    res_role = client.get("/api/users?role_id=1", headers=headers)
    assert res_role.status_code == 200
    assert all(str(u["role_id"]) == "1" for u in res_role.json()["items"])


def test_user_online_status_calculation(client):
    """2. Динамический расчет онлайн-статуса пользователя."""
    headers = get_admin_headers(client)
    res = client.get("/api/users?search=root", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    root_user = next(u for u in items if u["username"] == "root")
    # Поскольку у root активна сессия авторизации, флаг is_online должен быть True
    assert root_user["is_online"] is True


def test_user_creation_validation_and_uniqueness(client):
    """3. Модальное создание: Проверка уникальности username и генерации UID."""
    headers = get_admin_headers(client)

    # Успешное создание
    create_res = client.post("/api/users", json={
        "username": "unique_op_1",
        "password": "Password123!",
        "full_name": "Оператор 1",
        "email": "op1@nms.local",
        "role_id": "2"
    }, headers=headers)
    assert create_res.status_code == 200
    res_json = create_res.json()
    assert res_json["ok"] is True
    new_user_id = res_json["id"]

    # Проверка созданного пользователя через поиск
    created_user_res = client.get("/api/users?search=unique_op_1", headers=headers)
    assert created_user_res.status_code == 200
    created_user = created_user_res.json()["items"][0]
    assert created_user["username"] == "unique_op_1"
    assert created_user["uid"].startswith("UID-") or len(created_user["uid"]) > 0

    # Попытка создать дубликат по username -> 400 Bad Request
    dup_res = client.post("/api/users", json={
        "username": "unique_op_1",
        "password": "Password123!",
        "full_name": "Дубликат",
        "email": "dup@nms.local",
        "role_id": "2"
    }, headers=headers)
    assert dup_res.status_code == 400
    assert "существует" in dup_res.json()["detail"] or "exists" in dup_res.json()["detail"]


def test_user_edit_mutation(client):
    """4. Модальное редактирование: Смена роли, ФИО и блокировка."""
    headers = get_admin_headers(client)
    
    # 1. Создаем пользователя
    u_res = client.post("/api/users", json={
        "username": "edit_target", "password": "Password123!", "full_name": "Before Edit", "email": "before@nms.local", "role_id": "2"
    }, headers=headers)
    u_id = u_res.json()["id"]

    # 2. Обновляем данные
    edit_res = client.put(f"/api/users/{u_id}", json={
        "full_name": "After Edit Fullname",
        "email": "after@nms.local",
        "role_id": "3",
        "is_active": False
    }, headers=headers)
    assert edit_res.status_code == 200

    # 3. Проверяем в бд
    get_res = client.get(f"/api/users?search=edit_target", headers=headers)
    user_updated = get_res.json()["items"][0]
    assert user_updated["full_name"] == "After Edit Fullname"
    assert str(user_updated["role_id"]) == "3"
    assert user_updated["is_active"] is False or user_updated["is_active"] == 0


def test_user_sessions_monitoring_and_termination(client):
    """5. Управление сессиями пользователя и принудительное завершение."""
    headers = get_admin_headers(client)

    # 1. Создаем пользователя и логинимся под ним
    client.post("/api/users", json={
        "username": "sess_target", "password": "Password123!", "full_name": "Sess Target", "email": "s@nms.local", "role_id": "2"
    }, headers=headers)
    
    target_login = client.post("/api/auth/login", json={"username": "sess_target", "password": "Password123!"})
    target_token = target_login.json()["token"]
    target_user_id = target_login.json()["user"]["id"]

    # 2. Проверяем наличие активных сессий у пользователя
    user_sessions_res = client.get(f"/api/users/{target_user_id}/sessions", headers=headers)
    assert user_sessions_res.status_code == 200
    sessions = user_sessions_res.json()
    assert len(sessions) >= 1

    # 3. Принудительно завершаем все сессии пользователя от имени админа
    term_res = client.post(f"/api/users/{target_user_id}/terminate-sessions", headers=headers)
    assert term_res.status_code == 200

    # 4. Проверяем, что токен целевого пользователя больше НЕдействителен (401)
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {target_token}"}).status_code == 401


def test_superuser_protection_rules(client):
    """6. Защита суперпользователя от деструктивного отключения/удаления."""
    headers = get_admin_headers(client)
    res_me = client.get("/api/auth/me", headers=headers)
    root_id = res_me.json()["id"]

    # Попытка удалить аккаунт root -> 400 Bad Request
    del_res = client.delete(f"/api/users/{root_id}", headers=headers)
    assert del_res.status_code in (400, 403)
    assert "собственного пользователя" in del_res.json()["detail"] or "own" in del_res.json()["detail"]

    # Попытка отключить аккаунт root -> 400 Bad Request
    dis_res = client.put(f"/api/users/{root_id}", json={"is_active": False}, headers=headers)
    assert dis_res.status_code == 400
    assert "root" in dis_res.json()["detail"] or "super" in dis_res.json()["detail"]


def test_bulk_users_actions(client):
    """7 и 8. Массовые операции: Блокировка, разблокировка и завершение сессий."""
    headers = get_admin_headers(client)

    # Создаем 2 тестовых пользователей
    u1 = client.post("/api/users", json={"username": "bulk_u1", "password": "Password123!", "full_name": "B1", "email": "b1@nms.local", "role_id": "2"}, headers=headers).json()["id"]
    u2 = client.post("/api/users", json={"username": "bulk_u2", "password": "Password123!", "full_name": "B2", "email": "b2@nms.local", "role_id": "2"}, headers=headers).json()["id"]

    # A) Массовая блокировка
    lock_res = client.post("/api/users/bulk-action", json={"user_ids": [u1, u2], "action": "lock"}, headers=headers)
    assert lock_res.status_code == 200
    assert lock_res.json()["count"] == 2

    # B) Массовая разблокировка
    unlock_res = client.post("/api/users/bulk-action", json={"user_ids": [u1, u2], "action": "unlock"}, headers=headers)
    assert unlock_res.status_code == 200

    # C) Массовая смена роли
    role_res = client.post("/api/users/bulk-action", json={"user_ids": [u1, u2], "action": "set_role", "role_id": "3"}, headers=headers)
    assert role_res.status_code == 200


def test_disabled_auth_launch_option(client, monkeypatch):
    """9. Запуск с отключенной авторизацией (NMS_DISABLE_AUTH=1 / --no-auth)."""
    monkeypatch.setenv("NMS_DISABLE_AUTH", "1")
    # Проверка получения профиля без заголовок авторизации
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["auth_enabled"] is False
    assert data["username"] == "root"
    assert "system.all" in data["permissions"]

    # Доступ к защищенному списку пользователей без авторизации
    users_res = client.get("/api/users")
    assert users_res.status_code == 200

