"""REST API Endpoints for Auth, Users Management, RBAC Roles, and Audit Logs."""
from __future__ import annotations

import csv
import datetime
import io
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr

from backend.core.auth import (
    CurrentUser,
    create_access_token,
    get_current_user,
    require_permission,
)
from backend.core.audit import log_audit_event
from backend.core.database import get_db_connection, hash_password, verify_password
from backend.core.i18n import get_lang, tr
from backend.core.plugin.registry import get_security_settings, save_security_settings

router = APIRouter(prefix="/api", tags=["auth_users_rbac"])



# ── Схемы данных (Pydantic) ──────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]
    must_change_password: bool = False


class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str
    email: Optional[str] = None
    title: Optional[str] = None
    uid: Optional[str] = None
    role_id: str
    is_active: bool = True
    must_change_password: Optional[bool] = None


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    role_id: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    must_change_password: Optional[bool] = None


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
        sec_settings = get_security_settings()
        user = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.uid, u.avatar, u.hashed_password, u.is_active, u.role_id, r.name as role_name,
                   u.must_change_password, u.failed_login_attempts, u.locked_until
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = ?
            """,
            (body.username,),
        ).fetchone()

        now = datetime.datetime.now(datetime.timezone.utc)
        if user and user["locked_until"]:
            try:
                locked_until_dt = datetime.datetime.fromisoformat(str(user["locked_until"]))
                if locked_until_dt.tzinfo is None:
                    locked_until_dt = locked_until_dt.replace(tzinfo=datetime.timezone.utc)
                if now < locked_until_dt:
                    log_audit_event(
                        user_id=user["id"],
                        username=body.username,
                        action="auth.login_failed",
                        resource="auth",
                        details=tr(request, "Попытка входа в заблокированную учетную запись", "Login attempt on locked account"),
                        ip_address=request.client.host if request.client else None,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=tr(request, "Учетная запись временно заблокирована из-за превышения числа попыток входа", "Account temporarily locked due to too many failed attempts"),
                    )
            except HTTPException:
                raise
            except Exception:
                pass

        if not user or not verify_password(body.password, user["hashed_password"]):
            if user:
                failed_cnt = (user["failed_login_attempts"] or 0) + 1
                max_attempts = int(sec_settings.get("max_login_attempts", 5))
                lockout_duration = int(sec_settings.get("lockout_duration", 30))
                if failed_cnt >= max_attempts:
                    locked_until_time = (now + datetime.timedelta(minutes=lockout_duration)).isoformat()
                    conn.execute(
                        "UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?",
                        (failed_cnt, locked_until_time, user["id"]),
                    )
                    conn.commit()
                    log_audit_event(
                        user_id=user["id"],
                        username=body.username,
                        action="auth.login_lockout",
                        resource="auth",
                        details=tr(request, f"Учетная запись заблокирована на {lockout_duration} мин. из-за неверных входов", f"Account locked for {lockout_duration} mins due to failed attempts"),
                        ip_address=request.client.host if request.client else None,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=tr(request, f"Превышено число попыток. Учетная запись заблокирована на {lockout_duration} мин.", f"Max attempts exceeded. Account locked for {lockout_duration} mins."),
                    )
                else:
                    conn.execute("UPDATE users SET failed_login_attempts = ? WHERE id = ?", (failed_cnt, user["id"]))
                    conn.commit()

            log_audit_event(
                user_id=None,
                username=body.username,
                action="auth.login_failed",
                resource="auth",
                details=tr(request, "Неверное имя пользователя или пароль", "Invalid username or password"),
                ip_address=request.client.host if request.client else None,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=tr(request, "Неверное имя пользователя или пароль", "Invalid username or password"),
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=tr(request, "Учетная запись заблокирована", "Account is locked"),
            )

        # Сброс неверных входов при успешной аутентификации
        conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP, failed_login_attempts = 0, locked_until = NULL WHERE id = ?", (user["id"],))
        conn.commit()

        token = create_access_token(user["id"], user["username"])
        must_change = bool(user["must_change_password"])

        log_audit_event(
            user_id=user["id"],
            username=user["username"],
            action="auth.login_success",
            resource="auth",
            details=tr(request, "Успешный вход в систему", "Successful login"),
            ip_address=request.client.host if request.client else None,
        )

        return {
            "token": token,
            "must_change_password": must_change,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "email": user["email"],
                "uid": user["uid"],
                "role_id": user["role_id"],
                "role_name": user["role_name"],
                "avatar": user["avatar"],
                "must_change_password": must_change,
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
        details=tr(request, "Выход из системы", "Logged out"),
        ip_address=request.client.host if request and request.client else None,
    )
    return {"ok": True}


@router.post("/auth/terminate-sessions")
async def terminate_all_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    request: Request = None,
):
    """Завершение всех активных сессий пользователя на всех устройствах."""
    conn = get_db_connection()
    try:
        import time
        now_ts = int(time.time())
        conn.execute("UPDATE users SET token_valid_after = ? WHERE id = ?", (now_ts, current_user.id))
        conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="auth.terminate_all_sessions",
            resource="auth",
            details=tr(request, "Пользователь завершил все свои сессии на всех устройствах", "Terminated all user sessions across devices"),
            ip_address=request.client.host if request and request.client else None,
        )
        return {"ok": True}
    finally:
        conn.close()


@router.get("/auth/me")
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Получение информации о текущем авторизованном пользователе."""
    sec_settings = get_security_settings()
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
        "auth_enabled": sec_settings.get("auth_enabled", True),
    }


# ── 2. Users Management API ──────────────────────────────────────────
@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 100,
    search: Optional[str] = None,
    role_id: Optional[str] = None,
    current_user: CurrentUser = Depends(require_permission("users.manage")),
):
    """Получение списка всех пользователей с поддержкой пагинации, поиска и статуса активности."""
    conn = get_db_connection()
    try:
        sec_settings = get_security_settings()
        inactivity_timeout = int(sec_settings.get("inactivity_timeout_mins", 30))

        where_clauses = []
        params = []
        if search and search.strip():
            s = f"%{search.strip()}%"
            where_clauses.append("(u.username LIKE ? OR u.full_name LIKE ? OR u.email LIKE ? OR u.title LIKE ? OR u.uid LIKE ?)")
            params.extend([s, s, s, s, s])
        if role_id:
            where_clauses.append("u.role_id = ?")
            params.append(role_id)

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        total = conn.execute(f"SELECT COUNT(*) as cnt FROM users u {where_str}", params).fetchone()["cnt"]

        offset = max(0, (page - 1) * page_size)
        query_params = list(params) + [page_size, offset]

        rows = conn.execute(
            f"""
            SELECT u.id, u.username, u.full_name, u.email, u.title, u.uid, u.avatar, u.is_active, u.role_id, r.name as role_name,
                   u.created_at, u.last_login, u.last_seen, u.must_change_password, u.failed_login_attempts, u.locked_until
            FROM users u
            JOIN roles r ON u.role_id = r.id
            {where_str}
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?
            """,
            query_params,
        ).fetchall()

        now = datetime.datetime.now(datetime.timezone.utc)
        items = []
        for r in rows:
            u_dict = dict(r)
            # Динамическое вычисление реального онлайн-статуса
            is_online = False
            if u_dict.get("last_seen"):
                try:
                    last_seen_dt = datetime.datetime.fromisoformat(str(u_dict["last_seen"]))
                    if last_seen_dt.tzinfo is None:
                        last_seen_dt = last_seen_dt.replace(tzinfo=datetime.timezone.utc)
                    diff_mins = (now - last_seen_dt).total_seconds() / 60.0
                    if diff_mins <= inactivity_timeout:
                        is_online = True
                except Exception:
                    pass

            u_dict["is_online"] = is_online
            items.append(u_dict)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }
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
        user_uid = body.uid.strip() if (body.uid and body.uid.strip()) else f"UID-{uuid.uuid4().hex[:6].upper()}"

        # Проверка уникальности username и uid
        existing = conn.execute(
            "SELECT username, uid FROM users WHERE username = ? OR uid = ?",
            (body.username, user_uid),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=tr(request, "Пользователь с таким именем или UID уже существует", "User with this username or UID already exists"),
            )

        new_id = f"usr-{uuid.uuid4().hex[:8]}"
        hashed_pass = hash_password(body.password)

        sec_settings = get_security_settings()
        must_change = body.must_change_password if body.must_change_password is not None else bool(sec_settings.get("mandatory_password_change", False))

        conn.execute(
            """
            INSERT INTO users (id, username, full_name, email, title, uid, hashed_password, is_active, role_id, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id, body.username, body.full_name, body.email, body.title or "", user_uid, hashed_pass, int(body.is_active), body.role_id, int(must_change)),
        )
        conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="user.create",
            resource=f"user:{new_id}",
            details=tr(request, f"Создан пользователь {body.username} ({body.full_name})", f"Created user {body.username} ({body.full_name})"),
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
            raise HTTPException(status_code=404, detail=tr(request, "Пользователь не найден", "User not found"))

        updates = []
        params = []
        if body.full_name is not None:
            updates.append("full_name = ?")
            params.append(body.full_name)
        if body.email is not None:
            updates.append("email = ?")
            params.append(body.email)
        if body.title is not None:
            updates.append("title = ?")
            params.append(body.title)
        if body.role_id is not None:
            updates.append("role_id = ?")
            params.append(body.role_id)
        if body.is_active is not None:
            updates.append("is_active = ?")
            params.append(int(body.is_active))
        if body.must_change_password is not None:
            updates.append("must_change_password = ?")
            params.append(int(body.must_change_password))
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
                    detail=tr(
                        request,
                        "Нельзя отключить аккаунт root (или единственного суперадминистратора), пока не создан хотя бы один другой активный суперадминистратор",
                        "Cannot disable root account or the only superuser unless another active superuser exists",
                    ),
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
            details=tr(request, f"Обновлен пользователь {user['username']}", f"Updated user {user['username']}"),
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
        raise HTTPException(status_code=400, detail=tr(request, "Нельзя удалить собственного пользователя", "Cannot delete your own user account"))

    conn = get_db_connection()
    try:
        user = conn.execute("SELECT username, role_id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail=tr(request, "Пользователь не найден", "User not found"))

        if user["username"] == "root" or user["role_id"] == "1":
            other_superusers = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE role_id = '1' AND is_active = 1 AND id != ?",
                (user_id,),
            ).fetchone()["cnt"]
            if other_superusers == 0:
                raise HTTPException(
                    status_code=400,
                    detail=tr(
                        request,
                        "Нельзя удалить аккаунт root (или единственного суперадминистратора), пока не создан хотя бы один другой активный суперадминистратор",
                        "Cannot delete root account or the only superuser unless another active superuser exists",
                    ),
                )

        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="user.delete",
            resource=f"user:{user_id}",
            details=tr(request, f"Удален пользователь {user['username']}", f"Deleted user {user['username']}"),
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
            details=tr(request, "Пользователь обновил данные профиля", "User updated profile data"),
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
            raise HTTPException(status_code=400, detail=tr(request, "Текущий пароль указан неверно", "Current password is incorrect"))

        new_hash = hash_password(body.new_password)
        conn.execute("UPDATE users SET hashed_password = ?, must_change_password = 0 WHERE id = ?", (new_hash, current_user.id))
        conn.commit()

        log_audit_event(
            user_id=current_user.id,
            username=current_user.username,
            action="user.change_password",
            resource="profile",
            details=tr(request, "Пользователь изменил свой пароль", "User changed password"),
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
            details=tr(request, f"Создана роль {body.name}", f"Created role {body.name}"),
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
            raise HTTPException(status_code=404, detail=tr(request, "Роль не найдена", "Role not found"))

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
            details=tr(request, f"Обновлена роль {body.name}", f"Updated role {body.name}"),
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
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_user: CurrentUser = Depends(require_permission("audit.view")),
):
    """Получение журнала событий аудита с поддержкой серверной фильтрации."""
    conn = get_db_connection()
    try:
        where_clauses = []
        params = []
        if category == "errors":
            where_clauses.append("(action LIKE '%failed%' OR action LIKE '%delete%' OR action LIKE '%lockout%')")
        elif category == "auth":
            where_clauses.append("action LIKE 'auth.%'")
        elif category == "user":
            where_clauses.append("(action LIKE 'user.%' OR action LIKE 'role.%')")

        if search and search.strip():
            s = f"%{search.strip()}%"
            where_clauses.append("(username LIKE ? OR action LIKE ? OR resource LIKE ? OR details LIKE ? OR ip_address LIKE ?)")
            params.extend([s, s, s, s, s])

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        total = conn.execute(f"SELECT COUNT(*) as cnt FROM audit_logs {where_str}", params).fetchone()["cnt"]

        query_params = list(params) + [limit, offset]
        rows = conn.execute(
            f"""
            SELECT id, timestamp, user_id, username, action, resource, details, ip_address
            FROM audit_logs
            {where_str}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            query_params,
        ).fetchall()

        return {
            "total": total,
            "items": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@router.get("/audit-logs/export")
async def export_audit_logs(
    current_user: CurrentUser = Depends(require_permission("audit.view")),
):
    """Экспорт журнала событий аудита в формат CSV."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, timestamp, username, action, resource, details, ip_address
            FROM audit_logs
            ORDER BY id DESC
            """
        ).fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp", "Username", "Action", "Resource", "Details", "IP Address"])
        for r in rows:
            writer.writerow([r["id"], r["timestamp"], r["username"], r["action"], r["resource"], r["details"] or "", r["ip_address"] or ""])

        csv_content = output.getvalue()
        return Response(
            content=csv_content.encode("utf-8-sig"),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="audit_logs.csv"'},
        )
    finally:
        conn.close()


# ── 5. System Security Settings API ────────────────────────────────
class SecuritySettingsModel(BaseModel):
    auth_enabled: bool = True
    mandatory_password_change: bool = True
    max_login_attempts: int = 5
    lockout_duration: int = 30
    session_ttl_hours: int = 12
    inactivity_timeout_mins: int = 30
    force_mfa: bool = False


@router.get("/settings/security", response_model=SecuritySettingsModel)
async def get_security_settings_endpoint(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение глобальных настроек безопасности."""
    return get_security_settings()


@router.put("/settings/security")
async def update_security_settings_endpoint(
    body: SecuritySettingsModel,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("settings.edit")),
):
    """Обновление глобальных настроек безопасности."""
    save_security_settings(body.model_dump())
    log_audit_event(
        user_id=current_user.id,
        username=current_user.username,
        action="system.security_settings_updated",
        resource="settings",
        details=tr(request, "Обновлены параметры политики безопасности", "Updated security policy parameters"),
        ip_address=request.client.host if request and request.client else None,
    )
    return {"ok": True}

