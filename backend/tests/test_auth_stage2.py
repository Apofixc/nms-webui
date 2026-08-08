"""Тесты для Этапа 2 (Rate Limiting, Refresh-токены и MFA Recovery-коды)."""
import pytest
from backend.core.app import create_app
from backend.core.auth import generate_mfa_recovery_codes, verify_and_consume_recovery_code
from backend.core.database import get_db_connection
from backend.core.rate_limiter import rate_limiter
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def clear_rate_limiter_state():
    """Сброс состояния rate limiter перед каждым тестом."""
    rate_limiter.clear()


def test_login_rate_limiting():
    """Проверка срабатывания Rate Limiter при частых запросах к /api/auth/login."""
    app = create_app()
    client = TestClient(app)

    # Выполняем 5 неверных входов с несуществующим логином, чтобы не заблокировать аккаунт root
    for _ in range(5):
        resp = client.post("/api/auth/login", json={"username": "test_rate_user", "password": "wrong_password"})
        assert resp.status_code in (401, 429)

    # 6-й запрос должен превысить rate limit (429 RATE_LIMIT_EXCEEDED)
    resp = client.post("/api/auth/login", json={"username": "test_rate_user", "password": "wrong_password"})
    assert resp.status_code == 429
    data = resp.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_refresh_token_flow_and_rotation():
    """Проверка выпуска пары токенов, обновления через /api/auth/refresh и одноразовой ротации."""
    rate_limiter.clear()

    # Сброс аккаунта root в БД
    conn = get_db_connection()
    conn.execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE username = 'root'")
    conn.commit()
    conn.close()

    app = create_app()
    client = TestClient(app)

    # 1. Вход root пользователя
    resp = client.post("/api/auth/login", json={"username": "root", "password": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "refresh_token" in data
    old_refresh = data["refresh_token"]

    # 2. Обновление токенов через /api/auth/refresh
    resp_ref = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert resp_ref.status_code == 200
    data_ref = resp_ref.json()
    assert "access_token" in data_ref
    assert "refresh_token" in data_ref
    new_refresh = data_ref["refresh_token"]
    assert new_refresh != old_refresh

    # 3. Повторное использование старого refresh-токена должно приводить к отказу (401 SESSION_REVOKED)
    resp_old = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert resp_old.status_code == 401


def test_mfa_recovery_codes_flow():
    """Проверка генерации и одноразового гашения recovery-кодов MFA."""
    raw_codes, hashes_json = generate_mfa_recovery_codes(8)
    assert len(raw_codes) == 8

    conn = get_db_connection()
    try:
        # Привязываем кодам к пользователю root
        conn.execute("UPDATE users SET mfa_recovery_codes = ? WHERE username = 'root'", (hashes_json,))
        conn.commit()

        row = conn.execute("SELECT id FROM users WHERE username = 'root'").fetchone()
        user_id = row["id"]

        first_code = raw_codes[0]
        # Первый вызов должен гасить код и возвращать True
        assert verify_and_consume_recovery_code(user_id, first_code) is True

        # Повторный вызов тем же кодом должен возвращать False
        assert verify_and_consume_recovery_code(user_id, first_code) is False

        # Второй код из списка активен
        second_code = raw_codes[1]
        assert verify_and_consume_recovery_code(user_id, second_code) is True
    finally:
        conn.close()
