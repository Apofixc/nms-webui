"""REST API Endpoints for Auth, Users Management, RBAC Roles, and Audit Logs."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from backend.core.auth import (
    CurrentUser,
    create_access_token,
    get_current_user,
    require_permission,
)
from backend.core.audit import log_audit_event
from backend.core.database import get_db_connection, hash_password, verify_password

router = APIRouter(prefix="/api", tags=["auth_users_rbac"])


# ── Схемы данных (Pydantic) ──────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]


class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str
    email: Optional[str] = None
    uid: str
    role_id: str
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role_id: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class SelfUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class RoleCreateUpdateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    permission_ids: List[str] = []


# ── 1. Auth Endpoints ────────────────────────────────────────────────
@router.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request):
    """Вход пользователя в систему."""
    conn = get_db_connection()
    try:
        user = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.uid, u.avatar, u.hashed_password, u.is_active, u.role_id, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = ?
            """,
            (body.username,),
        ).fetchone()

        if not user or not verify_password(body.password, user["hashed_password"]):
            log_audit_event(
                user_id=None,
                username=body.username,
                action="auth.login_failed",
                resource="auth",
                details="Неверное имя пользователя или пароль",
                ip_address=request.client.host if request.client else None,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль",
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Учетная запись заблокирована",
            )

        # Обновление времени последнего входа
        conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
        conn.commit()

        token = create_access_token(user["id"], user["username"])

        log_audit_event(
            user_id=user["id"],
            username=user["username"],
            action="auth.login_success",
            resource="auth",
            details="Успешный вход в систему",
            ip_address=request.client.host if request.client else None,
        )

        return {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "email": user["email"],
                "uid": user["uid"],
                "role_id": user["role_id"],
                "role_name": user["role_name"],
                "avatar": user["avatar"],
            },
        }
    finally:
        conn.close()


@router.post("/auth/logout")
async def logout(current_user: CurrentUser = Depends(get_current_user), request: Request = None):
    """Выход пользователя из системы."""
    log_audit_event(
        user_id=current_user.id,
        username=current_user.username,
        action="auth.logout",
        resource="auth",
        details="Выход из системы",
        ip_address=request.client.host if request and request.client else None,
    )
    return {"ok": True}


@router.get("/auth/me")
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Получение информации о текущем авторизованном пользователе."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "uid": current_user.uid,
        "role_id": current_user.role_id,
        "role_name": current_user.role_name,
        "avatar": current_user.avatar,
        "permissions": current_user.permissions,
    }


# ── 2. Users Management API ──────────────────────────────────────────
@router.get("/users")
async def list_users(current_user: CurrentUser = Depends(get_current_user)):
    """Получение списка всех пользователей."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.uid, u.is_active, u.role_id, r.name as role_name, u.created_at, u.last_login
            FROM users u
            JOIN roles r ON u.role_id = r.id
            ORDER BY u.created_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/users")
async def create_user(
    body: UserCreateRequest,
    current_user: CurrentUser = Depends(require_permission("users.manage")),
    request: Request = None,
):
    """Создание нового пользователя."""
    conn = get_db_connection()
    try:
        # Проверка уникальности username и uid
        existing = conn.execute(
            "SELECT username, uid FROM users WHERE username = ? OR uid = ?",
            (body.username, body.uid),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем или UID уже существует",
            )

        new_id = f"usr-{uuid.uuid4().hex[:8]}"
        hashed_pass = hash_password(body.password)

        conn.execute(
            """
            INSERT INTO users (id, username, full_name, email, uid, hashed_password, is_active, role_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id, body.username, body.full_name, body.email, body.uid, hashed_pass, int(body.is_active), body.role_id),
        )
        conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="user.create",
            resource=f"user:{new_id}",
            details=f"Создан пользователь {body.username} ({body.full_name})",
            ip_address=request.client.host if request and request.client else None,
        )
        return {"ok": True, "id": new_id}
    finally:
        conn.close()


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("users.manage")),
    request: Request = None,
):
    """Редактирование пользователя."""
    conn = get_db_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        updates = []
        params = []
        if body.full_name is not None:
            updates.append("full_name = ?")
            params.append(body.full_name)
        if body.email is not None:
            updates.append("email = ?")
            params.append(body.email)
        if body.role_id is not None:
            updates.append("role_id = ?")
            params.append(body.role_id)
        if body.is_active is not None:
            updates.append("is_active = ?")
            params.append(int(body.is_active))
        if body.password and body.password.strip():
            updates.append("hashed_password = ?")
            params.append(hash_password(body.password))

        # Проверка защиты root от отключения / смены роли
        if (body.is_active is False or (body.role_id and body.role_id != '1')) and (user["username"] == "root" or user["role_id"] == "1"):
            other_superusers = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE role_id = '1' AND is_active = 1 AND id != ?",
                (user_id,),
            ).fetchone()["cnt"]
            if other_superusers == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Нельзя отключить аккаунт root (или единственного суперадминистратора), пока не создан хотя бы один другой активный суперадминистратор",
                )

        if updates:
            params.append(user_id)
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="user.update",
            resource=f"user:{user_id}",
            details=f"Обновлен пользователь {user['username']}",
            ip_address=request.client.host if request and request.client else None,
        )
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: CurrentUser = Depends(require_permission("users.manage")),
    request: Request = None,
):
    """Удаление пользователя."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить собственного пользователя")

    conn = get_db_connection()
    try:
        user = conn.execute("SELECT username, role_id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        if user["username"] == "root" or user["role_id"] == "1":
            other_superusers = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE role_id = '1' AND is_active = 1 AND id != ?",
                (user_id,),
            ).fetchone()["cnt"]
            if other_superusers == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Нельзя удалить аккаунт root (или единственного суперадминистратора), пока не создан хотя бы один другой активный суперадминистратор",
                )

        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="user.delete",
            resource=f"user:{user_id}",
            details=f"Удален пользователь {user['username']}",
            ip_address=request.client.host if request and request.client else None,
        )
        return {"ok": True}
    finally:
        conn.close()


@router.put("/users/me")
async def update_own_profile(
    body: SelfUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    request: Request = None,
):
    """Обновление собственного профиля текущим пользователем."""
    conn = get_db_connection()
    try:
        updates = []
        params = []
        if body.full_name is not None:
            updates.append("full_name = ?")
            params.append(body.full_name)
        if body.email is not None:
            updates.append("email = ?")
            params.append(body.email)
        if body.avatar is not None:
            updates.append("avatar = ?")
            params.append(body.avatar)

        if updates:
            params.append(current_user.id)
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="user.update_profile",
            resource="profile",
            details="Пользователь обновил данные профиля",
            ip_address=request.client.host if request and request.client else None,
        )
        return {"ok": True}
    finally:
        conn.close()


@router.put("/users/me/password")
async def change_own_password(
    body: PasswordChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    request: Request = None,
):
    """Смена собственного пароля."""
    conn = get_db_connection()
    try:
        user = conn.execute("SELECT hashed_password FROM users WHERE id = ?", (current_user.id,)).fetchone()
        if not verify_password(body.old_password, user["hashed_password"]):
            raise HTTPException(status_code=400, detail="Текущий пароль указан неверно")

        new_hash = hash_password(body.new_password)
        conn.execute("UPDATE users SET hashed_password = ? WHERE id = ?", (new_hash, current_user.id))
        conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="user.change_password",
            resource="profile",
            details="Пользователь изменил свой пароль",
            ip_address=request.client.host if request and request.client else None,
        )
        return {"ok": True}
    finally:
        conn.close()


# ── 3. Roles & Permissions API (RBAC) ────────────────────────────────
@router.get("/roles")
async def list_roles(current_user: CurrentUser = Depends(get_current_user)):
    """Получение списка ролей с привязанными правами."""
    conn = get_db_connection()
    try:
        roles_rows = conn.execute(
            """
            SELECT r.id, r.name, r.description, r.is_system, COUNT(u.id) as users_count
            FROM roles r
            LEFT JOIN users u ON u.role_id = r.id
            GROUP BY r.id
            """
        ).fetchall()

        res = []
        for r in roles_rows:
            perm_rows = conn.execute(
                "SELECT permission_id FROM role_permissions WHERE role_id = ?",
                (r["id"],),
            ).fetchall()
            perms = [p["permission_id"] for p in perm_rows]
            res.append({
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "is_system": bool(r["is_system"]),
                "users_count": r["users_count"],
                "permissions": perms,
            })
        return res
    finally:
        conn.close()


@router.get("/permissions")
async def list_permissions(current_user: CurrentUser = Depends(get_current_user)):
    """Получение списка всех доступных системных разрешений."""
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT id, category, name, description FROM permissions").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/roles")
async def create_role(
    body: RoleCreateUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("roles.manage")),
    request: Request = None,
):
    """Создание новой роли."""
    conn = get_db_connection()
    try:
        new_id = str(uuid.uuid4().hex[:8])
        conn.execute(
            "INSERT INTO roles (id, name, description, is_system) VALUES (?, ?, ?, 0)",
            (new_id, body.name, body.description),
        )
        for pid in body.permission_ids:
            conn.execute(
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                (new_id, pid),
            )
        conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="role.create",
            resource=f"role:{new_id}",
            details=f"Создана роль {body.name}",
            ip_address=request.client.host if request and request.client else None,
        )
        return {"ok": True, "id": new_id}
    finally:
        conn.close()


@router.put("/roles/{role_id}")
async def update_role(
    role_id: str,
    body: RoleCreateUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("roles.manage")),
    request: Request = None,
):
    """Обновление роли и матрицы ее разрешений."""
    conn = get_db_connection()
    try:
        role = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
        if not role:
            raise HTTPException(status_code=404, detail="Роль не найдена")

        conn.execute(
            "UPDATE roles SET name = ?, description = ? WHERE id = ?",
            (body.name, body.description, role_id),
        )
        # Перезапись разрешений
        conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
        for pid in body.permission_ids:
            conn.execute(
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                (role_id, pid),
            )
        conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="role.update",
            resource=f"role:{role_id}",
            details=f"Обновлена роль {body.name}",
            ip_address=request.client.host if request and request.client else None,
        )
        return {"ok": True}
    finally:
        conn.close()


# ── 4. Audit Logs API ────────────────────────────────────────────────
@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    current_user: CurrentUser = Depends(require_permission("audit.view")),
):
    """Получение журнала событий аудита."""
    conn = get_db_connection()
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM audit_logs").fetchone()["cnt"]
        rows = conn.execute(
            """
            SELECT id, timestamp, user_id, username, action, resource, details, ip_address
            FROM audit_logs
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        return {
            "total": total,
            "items": [dict(r) for r in rows],
        }
    finally:
        conn.close()
