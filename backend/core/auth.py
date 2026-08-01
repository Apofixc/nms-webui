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

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.database import get_db_connection
from backend.core.i18n import make_error_detail, tr

SECRET_KEY = "nms-secret-key-change-in-production"
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

    sig = hmac.new(
        SECRET_KEY.encode(),
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
        import traceback
        print("EXCEPTION IN CREATE_ACCESS_TOKEN:", e)
        traceback.print_exc()

    return f"{signing_input}.{s_bytes.decode()}"


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
            SECRET_KEY.encode(),
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=make_error_detail(request, "IP_ACCESS_DENIED", "ip_access_denied", client_ip=client_ip),
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=make_error_detail(request, "AUTH_REQUIRED", "auth_required"),
            headers={"WWW-Authenticate": "Bearer"},
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=make_error_detail(request, "INVALID_TOKEN", "invalid_token"),
            headers={"WWW-Authenticate": "Bearer"},
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=make_error_detail(request, "USER_NOT_FOUND_OR_LOCKED", "user_not_found_or_locked"),
            )

        valid_after = dict(row).get("token_valid_after") or 0
        if token_iat and token_iat <= valid_after:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=make_error_detail(request, "SESSION_REVOKED", "session_revoked"),
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Проверка индивидуального отзыва конкретной сессии
        if token_jti:
            sess_row = conn.execute("SELECT id, is_revoked FROM active_sessions WHERE token_jti = ?", (token_jti,)).fetchone()
            if sess_row and sess_row["is_revoked"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=make_error_detail(request, "SESSION_REVOKED_BY_ADMIN", "session_revoked_by_admin"),
                    headers={"WWW-Authenticate": "Bearer"},
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

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=make_error_detail(request, "INSUFFICIENT_PERMISSIONS", "insufficient_permissions", permission=permission),
        )

    return permission_checker


def require_module_permission(module_id: str, action: str = "view"):
    """Проверка включенности модуля в системе и наличии пермишена у роли пользователя."""
    from backend.core.plugin.registry import is_module_enabled

    async def module_permission_checker(request: Request = None, current_user: CurrentUser = Depends(get_current_user)):
        if not is_module_enabled(module_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=make_error_detail(request, "MODULE_DISABLED", "module_disabled", module_id=module_id),
            )

        if "system.all" in current_user.permissions:
            return current_user

        perm_key = f"module.{module_id}.{action}"
        if perm_key in current_user.permissions or f"{module_id}.{action}" in current_user.permissions:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=make_error_detail(request, "MODULE_INSUFFICIENT_PERMISSIONS", "module_insufficient_permissions", perm_key=perm_key, module_id=module_id),
        )

    return module_permission_checker

