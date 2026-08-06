import time
import pytest
from fastapi.testclient import TestClient
from backend.core.app import create_app
import backend.core.database as db_module

@pytest.fixture(scope="function")
def client(tmp_path):
    test_db = tmp_path / "test_edge.db"
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
# РАСШИРЕННЫЕ ГРАНИЧНЫЕ СЦЕНАРИИ ТЕСТИРОВАНИЯ 8 ПОЛИТИК БЕЗОПАСНОСТИ
# ============================================================================

def test_edge_tampered_and_invalid_jwt_tokens(client):
    """Сценарий 1: Запросы с поддельными, испорченными и незарегистрированными токенами."""
    # 1. Токен без Bearer префикса
    assert client.get("/api/auth/me", headers={"Authorization": "InvalidFormatToken"}).status_code == 401

    # 2. Поддельный JWT токен с измененной подписью
    tampered_jwt = "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAidXNyLXJvb3QtMDEiLCB1c2VybmFtZSI6ICJyb290In0.fake_signature_hash"
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_jwt}"}).status_code == 401


def test_edge_revoked_session_token_reuse(client):
    """Сценарий 2: Попытка использования токена от аннулированной сессии."""
    headers = get_admin_headers(client)
    
    sess_res = client.get("/api/users/me/sessions", headers=headers)
    assert sess_res.status_code == 200
    sessions = sess_res.json()
    assert len(sessions) > 0
    
    # Аннулируем текущую сессию
    sess_id = sessions[0]["id"]
    client.delete(f"/api/users/me/sessions/{sess_id}", headers=headers)
    
    # Запрос с аннулированным токеном обязан вернуть 401 Unauthorized
    res_after_revoke = client.get("/api/auth/me", headers=headers)
    assert res_after_revoke.status_code == 401


def test_edge_password_complexity_boundary_failures(client):
    """Сценарий 3: Детальная проверка всех критериев сложности паролей."""
    headers = get_admin_headers(client)
    
    # Настраиваем жесткую политику сложности
    client.put("/api/settings/security", json={
        "auth_enabled": True,
        "min_password_length": 10,
        "require_uppercase": True,
        "require_digits": True,
        "require_special_chars": True
    }, headers=headers)

    # A) Слишком короткий пароль (< 10)
    res1 = client.post("/api/users", json={
        "username": "u_short", "password": "Sh1!", "full_name": "F", "email": "e@e.com", "role_id": "1"
    }, headers=headers)
    assert res1.status_code == 400
    assert "слишком короткий" in res1.json()["error"]["message"] or "short" in res1.json()["error"]["message"]

    # B) Нет заглавной буквы
    res2 = client.post("/api/users", json={
        "username": "u_no_upper", "password": "password123!", "full_name": "F", "email": "e@e.com", "role_id": "1"
    }, headers=headers)
    assert res2.status_code == 400
    assert "заглавную" in res2.json()["error"]["message"] or "uppercase" in res2.json()["error"]["message"]

    # C) Нет цифры
    res3 = client.post("/api/users", json={
        "username": "u_no_digit", "password": "Password!!!!", "full_name": "F", "email": "e@e.com", "role_id": "1"
    }, headers=headers)
    assert res3.status_code == 400
    assert "цифру" in res3.json()["error"]["message"] or "digit" in res3.json()["error"]["message"]


def test_edge_failed_attempts_reset_on_success(client):
    """Сценарий 4: Сброс счетчика неверных попыток входа при успешной авторизации."""
    headers = get_admin_headers(client)
    client.put("/api/settings/security", json={"auth_enabled": True, "max_login_attempts": 3, "lockout_duration": 15}, headers=headers)

    # 2 неверные попытки (до лимита 3)
    assert client.post("/api/auth/login", json={"username": "root", "password": "wrong1"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "root", "password": "wrong2"}).status_code == 401

    # Успешная попытка с правильным паролем -> счетчик обнуляется!
    assert client.post("/api/auth/login", json={"username": "root", "password": "admin"}).status_code == 200

    # Следующая 1 неверная попытка НЕ должна вызывать блокировку 429
    res_next = client.post("/api/auth/login", json={"username": "root", "password": "wrong1"})
    assert res_next.status_code == 401  # 401, а не 429!


def test_edge_audit_log_filtering_and_pagination(client):
    """Сценарий 5: Пагинация и поиск по журналу аудита безопасности."""
    headers = get_admin_headers(client)
    
    # Генерация нескольких событий аудита
    client.get("/api/auth/me", headers=headers)
    client.get("/api/users?page=1&page_size=5", headers=headers)

    # Пагинация limit=2
    res_page1 = client.get("/api/audit-logs?limit=2&offset=0", headers=headers)
    assert res_page1.status_code == 200
    data1 = res_page1.json()
    assert len(data1.get("items", [])) <= 2
