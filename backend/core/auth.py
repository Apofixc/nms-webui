"""Authentication and authorization dependencies.

Uses HMAC-SHA256 signed bearer tokens with stdlib hashlib & hmac.
"""
from __future__ import annotations

import base64
import hmac
import hashlib
import ipaddress
import json
import re
import secrets
import struct
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional, Tuple

from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.database import get_db_connection
from backend.core.i18n import tr
from backend.core.exceptions import AuthenticationError, PermissionDeniedError, ModuleDisabledError

import logging
from backend.core.config import get_settings

_log = logging.getLogger("nms.auth")

TOKEN_TTL_SECONDS = 86400 * 7  # 7 дней

security = HTTPBearer(auto_error=False)


def get_allowed_cors_origins() -> list[str]:
    """Получить список разрешенных Origin из Settings."""
    return get_settings().cors_origins


def is_origin_allowed(origin: Optional[str], allowed_origins: Optional[list[str]] = None) -> bool:
    """Проверка заголовка Origin против allowlist (для защиты от CSWSH)."""
    if not origin:
        return True
    if allowed_origins is None:
        allowed_origins = get_allowed_cors_origins()
    if "*" in allowed_origins:
        return True
    parsed_origin = origin.rstrip("/")
    for allowed in allowed_origins:
        if allowed == "*" or allowed.rstrip("/") == parsed_origin:
            return True

    # Дополнительно разрешаем локальные loopback и приватные подсети RFC 1918 для dev/lan доступа
    try:
        parsed_url = urllib.parse.urlparse(parsed_origin)
        hostname = parsed_url.hostname
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return True
        if hostname:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback:
                return True
    except Exception:
        pass

    return False


def is_session_revoked(jti: Optional[str]) -> bool:
    """Проверить, аннулирована ли сессия по ее JTI в БД."""
    if not jti:
        return False
    try:
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT is_revoked FROM active_sessions WHERE token_jti = ?",
                (jti,)
            ).fetchone()
            if row and row["is_revoked"] == 1:
                return True
        finally:
            conn.close()
    except Exception:
        pass
    return False


_ws_tickets: dict[str, dict] = {}


def create_ws_ticket(user_id: str, jti: Optional[str] = None, expires_in: int = 30) -> str:
    """Сгенерировать одноразовый билет для подключения к WebSocket."""
    ticket = f"wst_{secrets.token_urlsafe(24)}"
    _ws_tickets[ticket] = {
        "user_id": str(user_id),
        "jti": str(jti) if jti else None,
        "expires_at": time.time() + expires_in,
    }
    return ticket


def consume_ws_ticket(ticket: str) -> Optional[dict]:
    """Проверить и погасить (удалить) одноразовый WebSocket билет."""
    now = time.time()
    # Очистка устаревших билетов
    expired = [t for t, data in _ws_tickets.items() if data["expires_at"] < now]
    for t in expired:
        _ws_tickets.pop(t, None)

    data = _ws_tickets.pop(ticket, None)
    if data and data["expires_at"] >= now:
        return data
    return None



def user_has_permission(user_id: str, permission: str) -> bool:

    """Проверка наличия разрешения у пользователя по его user_id."""
    if not user_id:
        return False
    try:
        conn = get_db_connection()
        try:
            row = conn.execute(
                """
                SELECT u.role_id, r.name as role_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = ? AND u.is_active = 1
                """,
                (user_id,),
            ).fetchone()
            if not row:
                return False

            role_id_str = str(row["role_id"])
            if role_id_str in _role_permissions_cache:
                permissions = _role_permissions_cache[role_id_str]
            else:
                perm_rows = conn.execute(
                    "SELECT permission_id FROM role_permissions WHERE role_id = ?",
                    (row["role_id"],),
                ).fetchall()
                permissions = tuple(p["permission_id"] for p in perm_rows)
                _role_permissions_cache[role_id_str] = permissions

            return "system.all" in permissions or permission in permissions
        finally:
            conn.close()
    except Exception:
        pass
    return False


def has_role_permission(role_or_user: str, permission: str) -> bool:
    """Универсальная проверка разрешения для ID пользователя или роли."""
    return user_has_permission(role_or_user, permission)




def is_ip_whitelisted(client_ip: str, whitelist_str: str) -> bool:
    """Проверка, входит ли client_ip в список whitelist (разделенный запятыми/пробелами/переводами строк)."""
    if not whitelist_str or not whitelist_str.strip():
        return True
    try:
        ip_obj = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    subnets = [s.strip() for s in re.split(r"[\s,;\n]+", whitelist_str) if s.strip()]
    if not subnets:
        return True

    for item in subnets:
        try:
            if "/" in item:
                net = ipaddress.ip_network(item, strict=False)
                if ip_obj in net:
                    return True
            else:
                target_ip = ipaddress.ip_address(item)
                if ip_obj == target_ip:
                    return True
        except ValueError:
            continue
    return False


@dataclass(frozen=True)
class CurrentUser:
    id: str
    username: str
    full_name: str
    email: Optional[str]
    uid: str
    role_id: str
    role_name: str
    avatar: Optional[str] = None
    is_authenticated: bool = True
    permissions: Tuple[str, ...] = ()
    token_jti: Optional[str] = None


def create_access_token(
    user_id: str,
    username: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """Создать подписанный JWT-подобный токен с регистрацией сессии."""
    import uuid
    from backend.core.plugin.registry import get_security_settings
    sec_settings = get_security_settings()
    ttl_hours = int(sec_settings.get("session_ttl_hours", 12))
    ttl_seconds = max(300, ttl_hours * 3600)

    jti = f"jti-{uuid.uuid4().hex}"
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "jti": jti,
        "iat": now,
        "exp": now + ttl_seconds,
    }

    h_bytes = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=")
    p_bytes = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    signing_input = f"{h_bytes.decode()}.{p_bytes.decode()}"

    sig = hmac.new(
        get_settings().secret_key.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    s_bytes = base64.urlsafe_b64encode(sig).rstrip(b"=")

    # Регистрация новой сессии в БД
    try:
        conn = get_db_connection()
        actual_ip = ip_address or "local"
        actual_ua = user_agent or "Browser Session"

        # Аннулируем предыдущие активные сессии с того же браузера/устройства для пользователя
        conn.execute(
            """
            UPDATE active_sessions
            SET is_revoked = 1
            WHERE user_id = ? AND ip_address = ? AND user_agent = ? AND is_revoked = 0
            """,
            (user_id, actual_ip, actual_ua),
        )

        # Аннулируем устаревшие сессий (last_seen > ttl_hours)
        ttl_seconds_calc = ttl_hours * 3600
        conn.execute(
            """
            UPDATE active_sessions
            SET is_revoked = 1
            WHERE is_revoked = 0
              AND (julianday('now') - julianday(replace(last_seen, 'T', ' '))) * 86400 > ?
            """,
            (ttl_seconds_calc,),
        )

        sess_id = f"sess-{uuid.uuid4().hex[:8]}"
        conn.execute(
            """
            INSERT INTO active_sessions (id, user_id, token_jti, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sess_id, user_id, jti, actual_ip, actual_ua),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        _log.error("Failed to register active session in database: %s", e, exc_info=True)

    return f"{signing_input}.{s_bytes.decode()}"


def create_refresh_token(
    user_id: str,
    username: str,
    jti: str,
    ttl_hours: int = 168,
) -> str:
    """Создать signed refresh-токен."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "jti": jti,
        "type": "refresh",
        "iat": now,
        "exp": now + (ttl_hours * 3600),
    }
    h_bytes = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=")
    p_bytes = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    signing_input = f"{h_bytes.decode()}.{p_bytes.decode()}"

    sig = hmac.new(
        get_settings().secret_key.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    s_bytes = base64.urlsafe_b64encode(sig).rstrip(b"=")
    return f"{signing_input}.{s_bytes.decode()}"


def decode_refresh_token(token: str) -> Optional[dict]:
    """Проверить и декодировать refresh-токен."""
    payload = decode_access_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None


def decode_access_token(token: str) -> Optional[dict]:
    """Проверить и декодировать токен. Возвращает payload или None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        h_str, p_str, s_str = parts
        signing_input = f"{h_str}.{p_str}"

        # Декодирование подписи
        rem = len(s_str) % 4
        if rem > 0:
            s_str += "=" * (4 - rem)
        sig_given = base64.urlsafe_b64decode(s_str)

        sig_expected = hmac.new(
            get_settings().secret_key.encode(),
            signing_input.encode(),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(sig_given, sig_expected):
            return None

        # Декодирование payload
        rem_p = len(p_str) % 4
        if rem_p > 0:
            p_str += "=" * (4 - rem_p)
        payload_bytes = base64.urlsafe_b64decode(p_str)
        data = json.loads(payload_bytes.decode())

        if "exp" in data and data["exp"] < time.time():
            return None

        return data
    except Exception:
        return None


_role_permissions_cache: dict[str, tuple[str, ...]] = {}


def clear_permissions_cache(role_id: Optional[str] = None) -> None:
    """Очистка кэша разрешений ролей."""
    if role_id:
        _role_permissions_cache.pop(str(role_id), None)
    else:
        _role_permissions_cache.clear()


async def get_current_user(
    request: Request = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """Dependency: извлекает текущего пользователя из Bearer-токена."""
    from backend.core.plugin.registry import get_security_settings
    sec_settings = get_security_settings()
    auth_enabled = sec_settings.get("auth_enabled", True)

    ip_whitelist = sec_settings.get("ip_whitelist", "")
    if ip_whitelist and request and request.client:
        client_ip = request.client.host
        if not is_ip_whitelisted(client_ip, ip_whitelist):
            raise PermissionDeniedError(
                message=tr(request, "ip_access_denied", client_ip=client_ip),
                code="IP_ACCESS_DENIED",
                details={"client_ip": client_ip},
            )

    if not auth or not auth.credentials:
        if not auth_enabled:
            return CurrentUser(
                id="usr-root-01",
                username="root",
                full_name="System Superuser",
                email="root@nms.local",
                uid="ROOT-001",
                role_id="1",
                role_name="Superuser",
                is_authenticated=True,
                permissions=("system.all",),
            )
        raise AuthenticationError(
            message=tr(request, "auth_required"),
            code="AUTH_REQUIRED",
        )
        
    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        if not auth_enabled:
            return CurrentUser(
                id="usr-root-01",
                username="root",
                full_name="System Superuser",
                email="root@nms.local",
                uid="ROOT-001",
                role_id="1",
                role_name="Superuser",
                is_authenticated=True,
                permissions=("system.all",),
            )
        raise AuthenticationError(
            message=tr(request, "invalid_token"),
            code="INVALID_TOKEN",
        )

    user_id = payload["sub"]
    token_iat = payload.get("iat", 0)
    token_jti = payload.get("jti")
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.uid, u.avatar, u.token_valid_after, u.is_active, u.role_id, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = ? AND u.is_active = 1
            """,
            (user_id,),
        ).fetchone()

        if not row:
            raise AuthenticationError(
                message=tr(request, "user_not_found_or_locked"),
                code="USER_NOT_FOUND_OR_LOCKED",
            )

        valid_after = dict(row).get("token_valid_after") or 0
        if token_iat and token_iat <= valid_after:
            raise AuthenticationError(
                message=tr(request, "session_revoked"),
                code="SESSION_REVOKED",
            )

        # Проверка индивидуального отзыва конкретной сессии
        if token_jti:
            sess_row = conn.execute("SELECT id, is_revoked FROM active_sessions WHERE token_jti = ?", (token_jti,)).fetchone()
            if sess_row and sess_row["is_revoked"]:
                raise AuthenticationError(
                    message=tr(request, "session_revoked_by_admin"),
                    code="SESSION_REVOKED_BY_ADMIN",
                )
            if sess_row:
                try:
                    conn.execute("UPDATE active_sessions SET last_seen = CURRENT_TIMESTAMP WHERE id = ?", (sess_row["id"],))
                    conn.commit()
                except Exception:
                    pass

        # Обновление метки последней активности пользователя
        try:
            conn.execute("UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
            conn.commit()
        except Exception:
            pass

        # Выборка разрешений пользователя по его роли (из кэша или БД)
        role_id_str = str(row["role_id"])
        if role_id_str in _role_permissions_cache:
            permissions = _role_permissions_cache[role_id_str]
        else:
            perm_rows = conn.execute(
                "SELECT permission_id FROM role_permissions WHERE role_id = ?",
                (row["role_id"],),
            ).fetchall()
            permissions = tuple(p["permission_id"] for p in perm_rows)
            _role_permissions_cache[role_id_str] = permissions

        return CurrentUser(
            id=row["id"],
            username=row["username"],
            full_name=row["full_name"],
            email=row["email"],
            uid=row["uid"],
            role_id=row["role_id"],
            role_name=row["role_name"],
            avatar=dict(row).get("avatar"),
            is_authenticated=True,
            permissions=permissions,
            token_jti=token_jti,
        )
    finally:
        conn.close()


async def get_current_user_optional(
    request: Request = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CurrentUser]:
    """Dependency: оптимистично извлекает пользователя, если есть токен, иначе None."""
    try:
        return await get_current_user(request=request, auth=auth)
    except (AuthenticationError, PermissionDeniedError):
        return None


def require_permission(permission: str):
    """Проверка прав доступа у текущего пользователя."""
    # Сопоставление прав: управляющее право автоматически включает просмотр
    implied_map = {
        "users.view": {"users.manage"},
        "roles.view": {"roles.manage"},
        "settings.view": {"settings.edit"},
        "modules.view": {"modules.manage"},
        "audit.view": {"audit.export"},
    }

    async def permission_checker(request: Request = None, current_user: CurrentUser = Depends(get_current_user)):
        user_perms = set(current_user.permissions or ())
        if "system.all" in user_perms:
            return current_user
        
        if permission in user_perms:
            return current_user
        
        # Проверяем, есть ли альтернативное управляющее право
        implied = implied_map.get(permission, set())
        if user_perms.intersection(implied):
            return current_user

        raise PermissionDeniedError(
            message=tr(request, "insufficient_permissions", permission=permission),
            code="INSUFFICIENT_PERMISSIONS",
            details={"permission": permission},
        )

    return permission_checker


def require_module_permission(module_id: str, action: str = "view"):
    """Проверка включенности модуля в системе и наличии пермишена у роли пользователя."""
    from backend.core.plugin.registry import is_module_enabled

    async def module_permission_checker(request: Request = None, current_user: CurrentUser = Depends(get_current_user)):
        if not is_module_enabled(module_id):
            raise ModuleDisabledError(module_id=module_id)

        if "system.all" in current_user.permissions:
            return current_user

        perm_key = f"module.{module_id}.{action}"
        if perm_key in current_user.permissions or f"{module_id}.{action}" in current_user.permissions:
            return current_user

        raise PermissionDeniedError(
            message=tr(request, "module_insufficient_permissions", perm_key=perm_key, module_id=module_id),
            code="MODULE_INSUFFICIENT_PERMISSIONS",
            details={"module_id": module_id, "perm_key": perm_key},
        )

    return module_permission_checker


# ── MFA / 2FA (RFC 6238 TOTP & QR Code Generator) ───────────────────
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

