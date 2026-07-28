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
    is_authenticated: bool = True
    permissions: Tuple[str, ...] = ()


def create_access_token(user_id: str, username: str) -> str:
    """Создать HMAC-подписанный токен авторизации."""
    payload = {
        "sub": user_id,
        "username": username,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS
    }
    raw_payload = base64.urlsafe_b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8').rstrip('=')
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        raw_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{raw_payload}.{signature}"


def decode_access_token(token: str) -> Optional[dict]:
    """Декодировать и проверить подпись и срок действия токена."""
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        raw_payload, signature = parts[0], parts[1]
        
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            raw_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
            
        padding = '=' * (4 - len(raw_payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(raw_payload + padding).decode('utf-8'))
        
        if data.get("exp", 0) < time.time():
            return None
            
        return data
    except Exception:
        return None


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """Dependency: извлекает текущего пользователя из Bearer-токена."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Необходима авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.uid, u.is_active, u.role_id, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = ? AND u.is_active = 1
            """,
            (user_id,),
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден или заблокирован",
            )

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
            is_authenticated=True,
            permissions=permissions,
        )
    finally:
        conn.close()


def require_permission(permission: str):
    """Проверка прав доступа у текущего пользователя."""
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)):
        if "system.all" in current_user.permissions:
            return current_user
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостаточно прав доступа ({permission})",
            )
        return current_user

    return permission_checker
