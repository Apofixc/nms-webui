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
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import logging
from backend.core.config import get_settings
from backend.core.database import get_db_connection
from backend.core.i18n import tr
from backend.core.exceptions import AuthenticationError, PermissionDeniedError, ModuleDisabledError

_log = logging.getLogger("nms.auth")
TOKEN_TTL_SECONDS = 86400 * 7  # 7 дней

security = HTTPBearer(auto_error=False)


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

    secret_key = get_settings().secret_key
    sig = hmac.new(
        secret_key.encode(),
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
        ttl_seconds = ttl_hours * 3600
        conn.execute(
            """
            UPDATE active_sessions
            SET is_revoked = 1
            WHERE is_revoked = 0
              AND (julianday('now') - julianday(replace(last_seen, 'T', ' '))) * 86400 > ?
            """,
            (ttl_seconds,),
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
        _log.error("Ошибка при сохранении сессии в create_access_token: %s", e, exc_info=True)

    return f"{signing_input}.{s_bytes.decode()}"


def create_token_pair(
    user_id: str,
    username: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:
    """Создать пару (access_token, refresh_token) с регистрацией активной сессии."""
    import uuid
    from backend.core.plugin.registry import get_security_settings
    sec_settings = get_security_settings()
    ttl_hours = int(sec_settings.get("session_ttl_hours", 12))
    access_ttl = 1800  # 30 минут
    refresh_ttl = max(3600, ttl_hours * 3600)

    now = int(time.time())
    secret_key = get_settings().secret_key

    # Access Token
    access_jti = f"jti-{uuid.uuid4().hex}"
    acc_payload = {
        "sub": user_id,
        "username": username,
        "jti": access_jti,
        "type": "access",
        "iat": now,
        "exp": now + access_ttl,
    }
    acc_h = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    acc_p = base64.urlsafe_b64encode(json.dumps(acc_payload).encode()).rstrip(b"=").decode()
    acc_input = f"{acc_h}.{acc_p}"
    acc_sig = base64.urlsafe_b64encode(hmac.new(secret_key.encode(), acc_input.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    access_token = f"{acc_input}.{acc_sig}"

    # Refresh Token
    refresh_jti = f"rjti-{uuid.uuid4().hex}"
    ref_payload = {
        "sub": user_id,
        "username": username,
        "jti": refresh_jti,
        "type": "refresh",
        "iat": now,
        "exp": now + refresh_ttl,
    }
    ref_h = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    ref_p = base64.urlsafe_b64encode(json.dumps(ref_payload).encode()).rstrip(b"=").decode()
    ref_input = f"{ref_h}.{ref_p}"
    ref_sig = base64.urlsafe_b64encode(hmac.new(secret_key.encode(), ref_input.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    refresh_token = f"{ref_input}.{ref_sig}"

    # Регистрация сессии в БД
    try:
        conn = get_db_connection()
        actual_ip = ip_address or "local"
        actual_ua = user_agent or "Browser Session"

        conn.execute(
            """
            UPDATE active_sessions
            SET is_revoked = 1
            WHERE user_id = ? AND ip_address = ? AND user_agent = ? AND is_revoked = 0
            """,
            (user_id, actual_ip, actual_ua),
        )

        sess_id = f"sess-{uuid.uuid4().hex[:8]}"
        conn.execute(
            """
            INSERT INTO active_sessions (id, user_id, token_jti, refresh_jti, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (sess_id, user_id, access_jti, refresh_jti, actual_ip, actual_ua),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        _log.error("Ошибка сохранения пары токенов: %s", e, exc_info=True)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": access_ttl,
    }


def generate_mfa_recovery_codes(count: int = 8) -> tuple[list[str], str]:
    """Сгенерировать одноразовые recovery-коды и их хеши для сохранения в БД."""
    import secrets
    raw_codes = []
    hashed_codes = []
    for _ in range(count):
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        code = f"{part1}-{part2}"
        raw_codes.append(code)
        clean_code = code.replace("-", "").upper()
        h = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()
        hashed_codes.append(h)
    return raw_codes, json.dumps(hashed_codes)


def verify_and_consume_recovery_code(user_id: str, raw_code: str) -> bool:
    """Проверить и погасить одноразовый recovery-код для пользователя."""
    if not raw_code:
        return False
    clean_code = raw_code.strip().replace("-", "").upper()
    if len(clean_code) < 8:
        return False

    code_hash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT mfa_recovery_codes FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not row["mfa_recovery_codes"]:
            return False

        try:
            hashes: list[str] = json.loads(row["mfa_recovery_codes"])
        except Exception:
            return False

        if code_hash in hashes:
            hashes.remove(code_hash)
            conn.execute("UPDATE users SET mfa_recovery_codes = ? WHERE id = ?", (json.dumps(hashes), user_id))
            conn.commit()
            return True
        return False
    finally:
        conn.close()


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

        secret_key = get_settings().secret_key
        sig_expected = hmac.new(
            secret_key.encode(),
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
                id="1",
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
                id="1",
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

