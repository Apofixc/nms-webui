"""Тесты проверки безопасности Этапа 1 (SECRET_KEY, crypto, headers)."""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from backend.core.config import get_settings
from backend.core.crypto import encrypt_secret, decrypt_secret, mask_secret
from backend.core.auth import create_access_token, decode_access_token
from backend.core.app import create_app


def test_crypto_encrypt_decrypt_and_fallback():
    plain = "super-secret-token-12345"
    encrypted = encrypt_secret(plain)
    assert encrypted != plain
    assert encrypted.startswith("enc:v1:")

    # Проверка дешифрования зашифрованного значения
    decrypted = decrypt_secret(encrypted)
    assert decrypted == plain

    # Проверка повторной попытки шифрования уже зашифрованной строки
    re_encrypted = encrypt_secret(encrypted)
    assert re_encrypted == encrypted

    # Плавная миграция: расшифровка не зашифрованной строки возвращает её как есть
    legacy_plain = "legacy_unencrypted_token"
    assert decrypt_secret(legacy_plain) == legacy_plain


def test_crypto_mask_secret():
    assert mask_secret("my_secret_token") == "***"
    assert mask_secret(None) is None
    assert mask_secret("") is None


def test_token_signing_and_key_change(monkeypatch):
    token = create_access_token("user-1", "admin")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-1"
    assert payload["username"] == "admin"

    # Смена SECRET_KEY должна делать старый токен невалидным
    monkeypatch.setenv("NMS_SECRET_KEY", "new-different-secret-key-999")
    get_settings.cache_clear()

    invalid_payload = decode_access_token(token)
    assert invalid_payload is None

    # Очищаем кэш настроек назад
    monkeypatch.delenv("NMS_SECRET_KEY", raising=False)
    get_settings.cache_clear()


def test_security_headers():
    app = create_app()
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in response.headers
