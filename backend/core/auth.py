"""Authentication and authorization dependencies.

Uses HMAC-SHA256 signed bearer tokens with stdlib hashlib & hmac.
"""
from __future__ import annotations

import base64
import hmac
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.database import get_db_connection
from backend.core.i18n import tr

SECRET_KEY = "nms-secret-key-change-in-production"
TOKEN_TTL_SECONDS = 86400 * 7  # 7 дней

security = HTTPBearer(auto_error=False)


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
        sess_id = f"sess-{uuid.uuid4().hex[:8]}"
        conn.execute(
            """
            INSERT INTO active_sessions (id, user_id, token_jti, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sess_id, user_id, jti, ip_address or "local", user_agent or "Browser Session"),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

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


async def get_current_user(
    request: Request = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """Dependency: извлекает текущего пользователя из Bearer-токена."""
    from backend.core.plugin.registry import get_security_settings
    sec_settings = get_security_settings()
    auth_enabled = sec_settings.get("auth_enabled", True)

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
            detail=tr(request, "Необходима авторизация", "Authentication required"),
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
            detail=tr(request, "Недействительный или просроченный токен", "Invalid or expired token"),
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
                detail=tr(request, "Пользователь не найден или заблокирован", "User not found or account is locked"),
            )

        valid_after = dict(row).get("token_valid_after") or 0
        if token_iat and token_iat < valid_after:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=tr(request, "Сессия аннулирована. Выполните повторный вход", "Session revoked. Please log in again"),
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Проверка индивидуального отзыва конкретной сессии
        if token_jti:
            sess_row = conn.execute("SELECT id, is_revoked FROM active_sessions WHERE token_jti = ?", (token_jti,)).fetchone()
            if sess_row and sess_row["is_revoked"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=tr(request, "Эта сессия была завершена администратором или пользователем", "This session has been revoked"),
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

        # Выборка разрешений пользователя по его роли
        perm_rows = conn.execute(
            "SELECT permission_id FROM role_permissions WHERE role_id = ?",
            (row["role_id"],),
        ).fetchall()
        permissions = tuple(p["permission_id"] for p in perm_rows)

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
            detail=tr(request, f"Недостаточно прав доступа ({permission})", f"Insufficient permissions ({permission})"),
        )

    return permission_checker


def require_module_permission(module_id: str, action: str = "view"):
    """Проверка включенности модуля в системе и наличии пермишена у роли пользователя."""
    from backend.core.plugin.registry import is_module_enabled

    async def module_permission_checker(request: Request = None, current_user: CurrentUser = Depends(get_current_user)):
        if not is_module_enabled(module_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=tr(request, f"Модуль '{module_id}' отключен в системе", f"Module '{module_id}' is disabled"),
            )

        if "system.all" in current_user.permissions:
            return current_user

        perm_key = f"module.{module_id}.{action}"
        if perm_key in current_user.permissions or f"{module_id}.{action}" in current_user.permissions:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=tr(request, f"Недостаточно прав ({perm_key}) для модуля '{module_id}'", f"Insufficient permissions ({perm_key}) for module '{module_id}'"),
        )

    return module_permission_checker

