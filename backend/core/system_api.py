"""System Administration API (Backup, Restore, Logs, Sessions)."""
from __future__ import annotations

import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from backend.core.auth import CurrentUser, require_permission
from backend.core.audit import log_audit_event
from backend.core.database import DB_PATH, get_db_connection
from backend.core.i18n import tr

router = APIRouter(prefix="/api/system", tags=["system"])

NMS_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_FILES = {
    "backend.log": NMS_ROOT / "backend.log",
    "astra.log": NMS_ROOT / "astra.log",
    "mcp-server.log": NMS_ROOT / "mcp-server.log",
}


@router.get("/backup")
async def download_backup(
    request: Request,
    user: CurrentUser = Depends(require_permission("settings.edit")),
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
    user: CurrentUser = Depends(require_permission("settings.edit")),
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
            details=f"База данных успешно восстановлена из {file.filename}",
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
    user: CurrentUser = Depends(require_permission("audit.view")),
):
    """Получить список имеющихся лог-файлов и их метаданные."""
    logs_info = []
    for name, path in LOG_FILES.items():
        exists = path.exists()
        size_bytes = path.stat().st_size if exists else 0
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime)) if exists else None
        logs_info.append({
            "name": name,
            "exists": exists,
            "size_bytes": size_bytes,
            "mtime": mtime,
        })
    return logs_info


@router.get("/logs/{log_name}")
async def get_log_content(
    log_name: str,
    request: Request,
    lines: int = 200,
    level: str = "ALL",
    search: str = "",
    user: CurrentUser = Depends(require_permission("audit.view")),
):
    """Чтение содержимого лог-файла с фильтрацией."""
    if log_name not in LOG_FILES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=tr(request, "Лог-файл не найден", "Log file not found"),
        )

    log_path = LOG_FILES[log_name]
    if not log_path.exists():
        return {"name": log_name, "content": [], "total_lines": 0}

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        filtered = []
        search_lower = search.lower().strip()
        level_upper = level.upper().strip()

        for line in all_lines:
            line_str = line.rstrip("\r\n")
            if search_lower and search_lower not in line_str.lower():
                continue
            if level_upper != "ALL":
                if level_upper not in line_str.upper():
                    continue
            filtered.append(line_str)

        result_lines = filtered[-max(1, min(lines, 2000)):]

        return {
            "name": log_name,
            "content": result_lines,
            "total_lines": len(all_lines),
            "matched_lines": len(filtered),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read log file: {exc}",
        )


@router.get("/sessions")
async def list_active_sessions(
    user: CurrentUser = Depends(require_permission("users.manage")),
):
    """Получить сводку активных пользователей."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.role_id, r.name as role_name,
                   u.last_login, u.is_active, u.token_valid_after
            FROM users u
            JOIN roles r ON u.role_id = r.id
            ORDER BY u.last_login DESC
            """
        ).fetchall()

        sessions = []
        for r in rows:
            sessions.append({
                "id": r["id"],
                "username": r["username"],
                "full_name": r["full_name"],
                "role_name": r["role_name"],
                "last_login": r["last_login"],
                "is_active": bool(r["is_active"]),
                "token_valid_after": r["token_valid_after"],
            })
        return sessions
    finally:
        conn.close()


@router.post("/sessions/terminate-all")
async def terminate_all_sessions(
    request: Request,
    user: CurrentUser = Depends(require_permission("users.manage")),
):
    """Сброс токенов пользователей (инвалидация сторонних сессий)."""
    now = int(time.time())
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("UPDATE users SET token_valid_after = ? WHERE id != ?", (now, user.id))

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
