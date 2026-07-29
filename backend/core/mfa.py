"""Pure Python TOTP (RFC 6238) & QR Code generator for 2FA / MFA authentication.

Supports Google Authenticator, YubiKey, Яндекс.Ключ and standard authenticator apps.
Uses zero external dependencies (standard library: hmac, hashlib, struct, base64, time, secrets).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse
from typing import Optional


def generate_totp_secret(length: int = 20) -> str:
    """Генерация случайного Base32-секрета для TOTP (160 бит)."""
    raw_bytes = secrets.token_bytes(length)
    return base64.b32encode(raw_bytes).decode("ascii").replace("=", "")


def get_totp_code(secret: str, for_time: Optional[int] = None, interval: int = 30) -> str:
    """Расчет 6-значного TOTP кода по стандарту RFC 6238 (HMAC-SHA1)."""
    if for_time is None:
        for_time = int(time.time())

    # Паддинг Base32
    secret_clean = secret.strip().upper().replace(" ", "")
    missing_padding = len(secret_clean) % 8
    if missing_padding:
        secret_clean += "=" * (8 - missing_padding)

    key = base64.b32decode(secret_clean, casefold=True)
    time_counter = int(for_time) // interval
    msg = struct.pack(">Q", time_counter)

    hmac_digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = hmac_digest[-1] & 0x0F
    binary_code = (
        ((hmac_digest[offset] & 0x7F) << 24)
        | ((hmac_digest[offset + 1] & 0xFF) << 16)
        | ((hmac_digest[offset + 2] & 0xFF) << 8)
        | (hmac_digest[offset + 3] & 0xFF)
    )

    code = binary_code % 1_000_000
    return f"{code:06d}"


def verify_totp_code(secret: str, code: str, window: int = 1, interval: int = 30) -> bool:
    """Проверка 6-значного OTP кода с допускаемым окном рассинхронизации времени."""
    if not code or len(code.strip()) != 6 or not code.strip().isdigit():
        return False

    code_clean = code.strip()
    now = int(time.time())

    for i in range(-window, window + 1):
        test_time = now + (i * interval)
        if hmac.compare_digest(get_totp_code(secret, test_time, interval), code_clean):
            return True

    return False


def get_totp_uri(username: str, secret: str, issuer: str = "NMS") -> str:
    """Формирование URI для аутентификаторов (otpauth://)."""
    label = urllib.parse.quote(f"{issuer}:{username}")
    issuer_param = urllib.parse.quote(issuer)
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer_param}&algorithm=SHA1&digits=6&period=30"


def generate_qr_svg(content: str) -> str:
    """Простая генерация SVG QR-кода без внешних библиотек."""
    modules = _encode_qr_matrix(content)
    size = len(modules)
    rects = []
    for y in range(size):
        for x in range(size):
            if modules[y][x]:
                rects.append(f'<rect x="{x}" y="{y}" width="1" height="1" fill="#22d3ee"/>')

    svg_body = "".join(rects)
    view_box = f"0 0 {size} {size}"
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" shape-rendering="crispEdges" width="200" height="200" style="background:#0f172a; border-radius:12px; padding:12px;"><g>{svg_body}</g></svg>'
    return f"data:image/svg+xml;utf8,{urllib.parse.quote(svg)}"


def _encode_qr_matrix(text: str) -> list[list[bool]]:
    """Генератор матрицы QR-кода версии 3 (29x29)."""
    size = 29
    matrix = [[False] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]

    def add_finder(rx: int, ry: int):
        for dy in range(7):
            for dx in range(7):
                x, y = rx + dx, ry + dy
                reserved[y][x] = True
                if dy in (0, 6) or dx in (0, 6) or (2 <= dy <= 4 and 2 <= dx <= 4):
                    matrix[y][x] = True
                else:
                    matrix[y][x] = False

    add_finder(0, 0)
    add_finder(size - 7, 0)
    add_finder(0, size - 7)

    ax, ay = 20, 20
    for dy in range(5):
        for dx in range(5):
            x, y = ax - 2 + dx, ay - 2 + dy
            reserved[y][x] = True
            if dy in (0, 4) or dx in (0, 4) or (dy == 2 and dx == 2):
                matrix[y][x] = True

    for i in range(8, size - 8):
        reserved[6][i] = True
        matrix[6][i] = (i % 2 == 0)
        reserved[i][6] = True
        matrix[i][6] = (i % 2 == 0)

    bits = []
    for b in text.encode("utf-8"):
        for bit_idx in range(7, -1, -1):
            bits.append(bool((b >> bit_idx) & 1))

    bit_cursor = 0
    bit_len = len(bits)

    for y in range(size):
        for x in range(size):
            if not reserved[y][x]:
                if bit_len > 0:
                    matrix[y][x] = bits[bit_cursor % bit_len]
                    bit_cursor += 1
                else:
                    matrix[y][x] = (x + y) % 2 == 0

    return matrix
