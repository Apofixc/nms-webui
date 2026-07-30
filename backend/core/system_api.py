"""System Administration API (Backup, Restore, Logs, Sessions)."""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse

from backend.core.auth import CurrentUser, decode_access_token, require_permission
from backend.core.audit import log_audit_event
from backend.core.database import DB_PATH, get_db_connection
from backend.core.i18n import tr
from backend.core.log_providers import log_provider_registry, matches_log_level
from backend.core.plugin.registry import get_security_settings

router = APIRouter(prefix="/api/system", tags=["system"])

NMS_ROOT = Path(__file__).resolve().parent.parent.parent
_matches_log_level = matches_log_level


@router.get("/backup")
async def download_backup(
    request: Request,
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Скачать резервную копию базы данных nms.db."""
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=tr(request, "Файл базы данных не найден", "Database file not found"),
        )

    filename = f"nms-backup-{time.strftime('%Y%m%d-%H%M%S')}.db"

    log_audit_event(
        user_id=user.id,
        username=user.username,
        action="SYSTEM_BACKUP",
        resource="system",
        details=f"Создан бэкап {filename}",
        ip_address=request.client.host if request.client else None,
    )

    return FileResponse(
        path=DB_PATH,
        filename=filename,
        media_type="application/x-sqlite3",
    )


@router.post("/restore")
async def restore_backup(
    request: Request,
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Восстановление системы из загруженного файла .db."""
    content = await request.body()
    if not content or len(content) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=tr(request, "Файл резервной копии пуст или не передан", "Backup file is empty or missing"),
        )

    temp_restore_path = DB_PATH.parent / "temp_restore.db"
    try:
        with open(temp_restore_path, "wb") as f:
            f.write(content)

        # Проверка целостности SQLite файла
        try:
            conn = sqlite3.connect(temp_restore_path)
            cur = conn.cursor()
            res = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
            conn.close()
            if not res:
                raise ValueError("Таблица 'users' не найдена в файле")
        except Exception as e:
            if temp_restore_path.exists():
                temp_restore_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=tr(request, f"Файл не является валидной БД NMS: {e}", f"Invalid backup file: {e}"),
            )

        # Резервная копия текущей БД
        backup_current = DB_PATH.parent / f"nms.db.bak_{int(time.time())}"
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, backup_current)

        # Замена базы данных
        shutil.move(temp_restore_path, DB_PATH)

        log_audit_event(
            user_id=user.id,
            username=user.username,
            action="SYSTEM_RESTORE",
            resource="system",
            details=f"База данных успешно восстановлена",
            ip_address=request.client.host if request.client else None,
        )

        return {"message": tr(request, "База данных успешно восстановлена", "Database restored successfully")}
    except HTTPException:
        raise
    except Exception as exc:
        if temp_restore_path.exists():
            temp_restore_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restoring backup: {exc}",
        )


@router.get("/logs")
async def list_available_logs(
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Получить список имеющихся источников логов (провайдеров)."""
    providers = await log_provider_registry.list_all()
    # Обратная совместимость с полем "name" (id)
    for p in providers:
        if "name" not in p or not p["name"]:
            p["name"] = p["id"]
    return providers


@router.get("/logs/{log_name}")
async def get_log_content(
    log_name: str,
    request: Request,
    lines: int = 200,
    level: str = "ALL",
    search: str = "",
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Чтение содержимого лога через зарегистрированный провайдер."""
    provider = log_provider_registry.get(log_name)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=tr(request, "Источник логов не найден", "Log provider not found"),
        )

    try:
        data = await provider.get_logs(lines=lines, level=level, search=search)
        if "name" not in data or not data["name"]:
            data["name"] = log_name
        return data
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read log provider: {exc}",
        )


@router.get("/logs/{log_name}/download")
async def download_log_file(
    log_name: str,
    request: Request,
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Скачивание полного файла лога через соответствующий провайдер."""
    provider = log_provider_registry.get(log_name)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=tr(request, "Источник логов не найден", "Log provider not found"),
        )

    content, filename, media_type = await provider.download_log()
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sessions")
async def list_active_sessions(
    request: Request,
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Получить список всех реальных активных сессий пользователей."""
    sec_settings = get_security_settings()
    ttl_hours = int(sec_settings.get("session_ttl_hours", 12))
    ttl_seconds = ttl_hours * 3600

    current_jti = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        payload = decode_access_token(auth_header.split(" ", 1)[1])
        if payload:
            current_jti = payload.get("jti")

    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.token_jti, s.user_id, u.username, u.full_name, r.name as role_name,
                   s.ip_address, s.user_agent, s.last_seen, s.created_at, u.is_active
            FROM active_sessions s
            JOIN users u ON s.user_id = u.id
            JOIN roles r ON u.role_id = r.id
            WHERE s.is_revoked = 0
              AND (julianday('now') - julianday(replace(s.last_seen, 'T', ' '))) * 86400 <= ?
            ORDER BY s.last_seen DESC
            """,
            (ttl_seconds,),
        ).fetchall()

        sessions = []
        for r in rows:
            sessions.append({
                "id": r["id"],
                "token_jti": r["token_jti"],
                "user_id": r["user_id"],
                "username": r["username"],
                "full_name": r["full_name"],
                "role_name": r["role_name"],
                "ip_address": r["ip_address"],
                "user_agent": r["user_agent"],
                "last_seen": r["last_seen"],
                "created_at": r["created_at"],
                "is_active": True,
                "is_current": bool(current_jti and r["token_jti"] == current_jti),
            })
        return sessions
    finally:
        conn.close()


@router.post("/sessions/terminate-all")
async def terminate_all_sessions(
    request: Request,
    keep_current: bool = True,
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Сброс токенов пользователей (инвалидация сторонних сессий)."""
    now = int(time.time())

    current_jti = user.token_jti
    if not current_jti and request:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            payload = decode_access_token(auth_header.split(" ", 1)[1])
            if payload:
                current_jti = payload.get("jti")

    conn = get_db_connection()
    try:
        with conn:
            if keep_current and current_jti:
                conn.execute("UPDATE active_sessions SET is_revoked = 1 WHERE token_jti != ?", (current_jti,))
                conn.execute("UPDATE users SET token_valid_after = ? WHERE id != ?", (now, user.id))
            else:
                conn.execute("UPDATE active_sessions SET is_revoked = 1")
                conn.execute("UPDATE users SET token_valid_after = ?", (now,))

        log_audit_event(
            user_id=user.id,
            username=user.username,
            action="TERMINATE_ALL_SESSIONS",
            resource="security",
            details="Аннулированы сторонние сессии пользователей",
            ip_address=request.client.host if request.client else None,
        )
        return {"message": tr(request, "Все сторонние сессии пользователей успешно аннулированы", "All user sessions terminated successfully")}
    finally:
        conn.close()
