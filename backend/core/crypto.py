"""Утилита шифрования секретов at-rest (AES-GCM с HKDF)."""
from __future__ import annotations

import base64
import os
from functools import lru_cache
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.core.config import get_settings

PREFIX = "enc:v1:"


@lru_cache
def _get_aes_key(secret_key: str) -> bytes:
    """Вывести 256-битный ключ шифрования из secret_key с помощью HKDF."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"nms-webui-at-rest-salt",
        info=b"secret-encryption-v1",
    )
    return hkdf.derive(secret_key.encode("utf-8"))


def encrypt_secret(plain_text: str | None) -> str | None:
    """Зашифровать чувствительные данные.

    Если строка пустая или уже зашифрована (начинается с enc:v1:), возвращает исходное значение.
    """
    if not plain_text:
        return plain_text

    if plain_text.startswith(PREFIX):
        return plain_text

    key = _get_aes_key(get_settings().secret_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plain_text.encode("utf-8"), None)
    encoded = base64.b64encode(nonce + ciphertext).decode("utf-8")
    return f"{PREFIX}{encoded}"


def decrypt_secret(cipher_text: str | None) -> str | None:
    """Расшифровать данные.

    Если значение незашифровано (старый формат), возвращает его как есть (плавная миграция).
    """
    if not cipher_text:
        return cipher_text

    if not cipher_text.startswith(PREFIX):
        return cipher_text

    try:
        raw_b64 = cipher_text[len(PREFIX):]
        raw_data = base64.b64decode(raw_b64)
        nonce = raw_data[:12]
        ciphertext = raw_data[12:]
        key = _get_aes_key(get_settings().secret_key)
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode("utf-8")
    except Exception:
        # Fallback при ошибке дешифрования
        return cipher_text


def mask_secret(secret_val: str | None) -> str | None:
    """Маскировать секрет для API ответов."""
    if not secret_val:
        return None
    return "***"
