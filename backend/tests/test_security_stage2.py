"""Тесты проверки безопасности Этапа 2 (Rate limiter, Refresh-токены, MFA Recovery)."""
from __future__ import annotations

import json
import pytest
from backend.core.rate_limiter import RateLimiter
from backend.core.auth import create_refresh_token, decode_refresh_token
from backend.api.users import generate_mfa_recovery_codes, verify_and_consume_recovery_code
from backend.core.database import get_db_connection, init_db


def test_rate_limiter_sliding_window():
    limiter = RateLimiter()
    key = "test_ip_127.0.0.1:user1"

    # Разрешаем 3 запроса
    for _ in range(3):
        assert limiter.is_rate_limited(key, max_requests=3, window_seconds=60) is False

    # 4-й запрос заблокирован
    assert limiter.is_rate_limited(key, max_requests=3, window_seconds=60) is True


def test_refresh_token_flow():
    token = create_refresh_token("user-100", "john", jti="jti-test-123")
    payload = decode_refresh_token(token)

    assert payload is not None
    assert payload["sub"] == "user-100"
    assert payload["username"] == "john"
    assert payload["type"] == "refresh"
    assert payload["jti"] == "jti-test-123"


def test_mfa_recovery_codes_generation_and_consumption():
    init_db()
    plain_codes, hashed_codes = generate_mfa_recovery_codes(count=5)

    assert len(plain_codes) == 5
    assert len(hashed_codes) == 5

    hashes_json = json.dumps(hashed_codes)
    test_user_id = "test_user_rec_1"

    conn = get_db_connection()
    try:
        # Проверяем верный код
        code_to_test = plain_codes[0]
        consumed = verify_and_consume_recovery_code(test_user_id, code_to_test, hashes_json, conn)
        assert consumed is True

        # Нельзя использовать тот же код дважды с обновленным списком
        updated_hashes = conn.execute("SELECT mfa_recovery_codes FROM users WHERE id = ?", (test_user_id,)).fetchone()
        if updated_hashes and updated_hashes["mfa_recovery_codes"]:
            second_attempt = verify_and_consume_recovery_code(test_user_id, code_to_test, updated_hashes["mfa_recovery_codes"], conn)
            assert second_attempt is False

        # Неверный код отклоняется
        invalid_attempt = verify_and_consume_recovery_code(test_user_id, "WRONG-CODE", hashes_json, conn)
        assert invalid_attempt is False
    finally:
        conn.close()
