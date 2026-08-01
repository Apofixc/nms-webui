import asyncio
import os
import re
import shutil
import sqlite3
import time
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.core.auth import CurrentUser, decode_access_token, require_permission
from backend.core.audit import log_audit_event
from backend.core.database import DB_PATH, get_db_connection
from backend.core.i18n import make_error_detail, tr
from backend.core.log_providers import RemoteHTTPLogProvider, log_provider_registry, matches_log_level
from backend.core.plugin.registry import (
    get_all_instances,
    get_all_manifests,
    get_security_settings,
    is_module_enabled,
)

router = APIRouter(prefix="/api/system", tags=["system"])

NMS_ROOT = Path(__file__).resolve().parent.parent.parent
_matches_log_level = matches_log_level


@router.get("/health")
async def get_system_health():
    """Детализированный статус здоровья системы (БД, диск, модули)."""
    db_status = {"status": "ok"}
    overall_status = "ok"
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
    except Exception as exc:
        db_status = {"status": "error", "error": str(exc)}
        overall_status = "degraded"

    # Disk usage
    disk_info = {}
    try:
        total, used, free = shutil.disk_usage(NMS_ROOT)
        disk_info = {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "percent_used": round((used / total) * 100, 1),
        }
        if disk_info["percent_used"] > 95:
            overall_status = "degraded"
    except Exception:
        disk_info = {"status": "unknown"}

    # Modules status
    manifests = get_all_manifests()
    instances = get_all_instances()
    modules_health = []
    for m in manifests:
        enabled = is_module_enabled(m.id, m.enabled_by_default)
        has_inst = m.id in instances
        mod_status = "active" if (enabled and has_inst) else ("disabled" if not enabled else "loaded")
        modules_health.append({
            "id": m.id,
            "name": m.name or m.id,
            "enabled": enabled,
            "has_instance": has_inst,
            "status": mod_status,
        })

    return {
        "status": overall_status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "database": db_status,
        "disk": disk_info,
        "modules": modules_health,
    }


class RemoteLogSourceCreate(BaseModel):
    name: str
    url: str
    api_token: Optional[str] = None


@router.get("/backup")
async def download_backup(
    request: Request,
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Скачать резервную копию базы данных nms.db."""
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=make_error_detail(request, "DB_FILE_NOT_FOUND", "db_file_not_found"),
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
            detail=make_error_detail(request, "BACKUP_FILE_EMPTY", "backup_file_empty"),
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
                detail=make_error_detail(request, "DB_INVALID_BACKUP", "db_invalid_backup", exc=str(e)),
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

        return {"message": tr(request, "db_restored_success")}
    except HTTPException:
        raise
    except Exception as exc:
        if temp_restore_path.exists():
            temp_restore_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=make_error_detail(request, "DB_RESTORE_ERROR", "db_restore_error", exc=str(exc)),
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
            detail=make_error_detail(request, "LOG_PROVIDER_NOT_FOUND", "log_provider_not_found"),
        )

    try:
        data = await provider.get_logs(lines=lines, level=level, search=search)
        if "name" not in data or not data["name"]:
            data["name"] = log_name
        return data
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=make_error_detail(request, "LOG_READ_ERROR", "log_read_error", exc=str(exc)),
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
            detail=make_error_detail(request, "LOG_PROVIDER_NOT_FOUND", "log_provider_not_found"),
        )

    content, filename, media_type = await provider.download_log()
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/logs/remote-sources/list")
async def list_remote_log_sources(
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Получить список зарегистрированных удаленных серверов логов."""
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT id, name, url, api_token, created_at FROM remote_log_sources ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/logs/remote-sources")
async def add_remote_log_source(
    payload: RemoteLogSourceCreate,
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Добавить новый удаленный сервер логов."""
    source_id = f"remote_{uuid.uuid4().hex[:8]}"
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO remote_log_sources (id, name, url, api_token) VALUES (?, ?, ?, ?)",
                (source_id, payload.name, payload.url, payload.api_token),
            )
        headers = {}
        if payload.api_token:
            headers["Authorization"] = f"Bearer {payload.api_token}"
        provider = RemoteHTTPLogProvider(
            provider_id=source_id,
            name=payload.name,
            url=payload.url,
            headers=headers,
            category="remote",
        )
        log_provider_registry.register(provider)
        return {"id": source_id, "name": payload.name, "url": payload.url}
    finally:
        conn.close()


@router.delete("/logs/remote-sources/{source_id}")
async def delete_remote_log_source(
    source_id: str,
    user: CurrentUser = Depends(require_permission("system.admin")),
):
    """Удалить удаленный сервер логов."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM remote_log_sources WHERE id = ?", (source_id,))
        log_provider_registry.unregister(source_id)
        return {"ok": True, "id": source_id}
    finally:
        conn.close()


@router.websocket("/logs/{log_name}/stream")
async def stream_log_websocket(websocket: WebSocket, log_name: str, level: str = "ALL", search: str = ""):
    """WebSocket стриминг логов в реальном времени."""
    await websocket.accept()
    provider = log_provider_registry.get(log_name)
    if not provider:
        await websocket.close(code=1008, reason="Log provider not found")
        return

    last_lines_count = 0
    try:
        while True:
            data = await provider.get_logs(lines=200, level=level, search=search)
            content = data.get("content", [])
            if len(content) != last_lines_count:
                last_lines_count = len(content)
                await websocket.send_json({
                    "id": provider.id,
                    "name": provider.name,
                    "content": content,
                    "matched_lines": len(content),
                    "total_lines": data.get("total_lines", len(content)),
                })
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


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
        return {"message": tr(request, "all_sessions_terminated")}
    finally:
        conn.close()
