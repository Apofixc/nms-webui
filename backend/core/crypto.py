"""Шифрование чувствительных данных at-rest (AES-256-GCM).

Использует ключ, получаемый через HKDF-SHA256 из NMS_SECRET_KEY.
Формат зашифрованных данных: enc:v1:<base64_iv>:<base64_ciphertext>
"""
from __future__ import annotations

import base64
import logging
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from backend.core.config import get_settings

_log = logging.getLogger("nms.crypto")
_AES_KEY: bytes | None = None
_LAST_SECRET_KEY: str | None = None

PREFIX = "enc:v1:"
HKDF_SALT = b"nms-secret-encryption-v1"
HKDF_INFO = b"aes-gcm-at-rest"


def _get_aes_key() -> bytes:
    """Получить или вывести 256-битный AES ключ из secret_key через HKDF."""
    global _AES_KEY, _LAST_SECRET_KEY
    current_secret = get_settings().secret_key

    if _AES_KEY is not None and _LAST_SECRET_KEY == current_secret:
        return _AES_KEY

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=HKDF_SALT,
        info=HKDF_INFO,
    )
    _AES_KEY = hkdf.derive(current_secret.encode("utf-8"))
    _LAST_SECRET_KEY = current_secret
    return _AES_KEY


def encrypt_secret(plaintext: str | None) -> str | None:
    """Зашифровать чувствительную строку в формат enc:v1:<iv>:<ciphertext>.

    Если значение зашифровано или пустое, возвращается как есть.
    """
    if not plaintext or plaintext.startswith(PREFIX):
        return plaintext

    try:
        key = _get_aes_key()
        aesgcm = AESGCM(key)
        iv = os.urandom(12)
        ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)

        b64_iv = base64.urlsafe_b64encode(iv).decode("utf-8")
        b64_ct = base64.urlsafe_b64encode(ciphertext).decode("utf-8")
        return f"{PREFIX}{b64_iv}:{b64_ct}"
    except Exception as exc:
        _log.error("Ошибка при шифровании секрета: %s", exc)
        return plaintext


def decrypt_secret(ciphertext: str | None) -> str | None:
    """Расшифровать строку формата enc:v1:<iv>:<ciphertext>.

    Если строка не содержит префикса enc:v1:, она возвращается как открытый текст (плавная миграция).
    """
    if not ciphertext or not ciphertext.startswith(PREFIX):
        return ciphertext

    try:
        payload = ciphertext[len(PREFIX):]
        parts = payload.split(":")
        if len(parts) != 2:
            return ciphertext

        b64_iv, b64_ct = parts
        iv = base64.urlsafe_b64decode(b64_iv.encode("utf-8"))
        ct = base64.urlsafe_b64decode(b64_ct.encode("utf-8"))

        key = _get_aes_key()
        aesgcm = AESGCM(key)
        plaintext_bytes = aesgcm.decrypt(iv, ct, None)
        return plaintext_bytes.decode("utf-8")
    except Exception as exc:
        _log.error("Ошибка при расшифровке секрета: %s", exc)
        return ciphertext


def mask_secret(val: str | None) -> str | None:
    """Маскирование значения секрета для безопасного вывода в API."""
    if not val:
        return val
    return "***"
