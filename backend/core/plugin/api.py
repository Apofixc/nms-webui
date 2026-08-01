import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel

from backend.core.auth import CurrentUser, require_permission
from backend.core.i18n import make_error_detail, tr
from backend.core.plugin.registry import (
    get_all_widgets,
    get_instance,
    get_loaded_modules,
    get_manifest,
    get_module_enable_config_schema,
    get_module_settings,
    get_module_settings_definition,
    get_module_views,
    get_modules,
    save_module_settings,
    set_module_enabled,
    unregister_manifest,
)
from backend.core.plugin.loader import scan_and_register_modules, unload_single_module, _load_single_manifest

router = APIRouter(prefix="/api/modules", tags=["modules"])


class EnableBody(BaseModel):
    enabled: bool


@router.get("")
async def list_modules(
    with_settings: bool = False,
    only_enabled: bool = False,
    user: CurrentUser = Depends(require_permission("modules.view")),
) -> dict[str, Any]:
    """Список модулей и их состояние."""
    items = get_modules(with_settings=with_settings, only_enabled=only_enabled)
    return {"items": items}


@router.get("/loaded")
async def loaded_modules(
    user: CurrentUser = Depends(require_permission("modules.view")),
) -> dict[str, Any]:
    """Список ID загруженных (включённых) модулей."""
    return {"items": get_loaded_modules()}


@router.get("/widgets")
async def list_module_widgets(
    user: CurrentUser = Depends(require_permission("modules.view")),
) -> dict[str, Any]:
    """Получить список виджетов включенных модулей."""
    return {"items": get_all_widgets()}


@router.post("/scan")
async def scan_modules_endpoint(
    request: Request,
    user: CurrentUser = Depends(require_permission("modules.manage")),
) -> dict[str, Any]:
    """Сканирование директории modules/ на новые модули."""
    manifests = scan_and_register_modules(request.app)
    return {"ok": True, "count": len(manifests), "items": [m.to_api_dict() for m in manifests]}


@router.post("/install")
async def install_module_endpoint(
    request: Request,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_permission("modules.manage")),
) -> dict[str, Any]:
    """Установка модуля из ZIP-архива по эталонной структуре."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(request, "MODULE_FILE_MUST_BE_ZIP", "module_file_must_be_zip"),
        )

    project_root = Path(__file__).resolve().parent.parent.parent.parent

    try:
        with zipfile.ZipFile(file.file, "r") as zip_ref:
            # Манифест должен присутствовать в архиве по пути backend/modules/{id}/manifest.yaml
            manifest_entry = next((name for name in zip_ref.namelist() if name.endswith("manifest.yaml") or name.endswith("manifest.yml")), None)
            if not manifest_entry:
                raise HTTPException(
                    status_code=400,
                    detail=make_error_detail(request, "MODULE_MISSING_MANIFEST", "module_missing_manifest"),
                )

            import yaml
            manifest_data = yaml.safe_load(zip_ref.read(manifest_entry))
            if not isinstance(manifest_data, dict) or not manifest_data.get("id"):
                raise HTTPException(
                    status_code=400,
                    detail=make_error_detail(request, "MODULE_INVALID_MANIFEST", "module_invalid_manifest"),
                )

            module_id = str(manifest_data["id"]).split(".")[0]

            # Проверка ZipSlip безопасности
            for member in zip_ref.infolist():
                if ".." in member.filename.split("/"):
                    raise HTTPException(
                        status_code=400,
                        detail=make_error_detail(request, "MODULE_UNSAFE_PATH", "module_unsafe_path"),
                    )

            # Распаковка строго по эталонным путям проекта
            backend_target = project_root / "backend" / "modules" / module_id
            frontend_target = project_root / "frontend" / "src" / "modules" / module_id

            backend_prefix = f"backend/modules/{module_id}/"
            frontend_prefix = f"frontend/src/modules/{module_id}/"

            for member in zip_ref.infolist():
                if member.is_dir():
                    continue

                if member.filename.startswith(backend_prefix):
                    rel_file = member.filename[len(backend_prefix):]
                    out_path = backend_target / rel_file
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(zip_ref.read(member.filename))
                elif member.filename.startswith(frontend_prefix):
                    rel_file = member.filename[len(frontend_prefix):]
                    out_path = frontend_target / rel_file
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(zip_ref.read(member.filename))

        scan_and_register_modules(request.app)
        manifest = get_manifest(module_id)
        return {
            "ok": True,
            "module_id": module_id,
            "manifest": manifest.to_api_dict() if manifest else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=make_error_detail(request, "MODULE_INSTALL_ERROR", "module_install_error", exc=str(exc)),
        )


@router.get("/{module_id}/export")
async def export_module_endpoint(
    module_id: str,
    request: Request,
    user: CurrentUser = Depends(require_permission("modules.view")),
) -> Response:
    """Упаковка модуля в ZIP-архив и скачивание по эталонной структуре."""
    import io
    manifest = get_manifest(module_id)
    if not manifest:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(request, "MODULE_NOT_FOUND", "module_not_found"),
        )

    root_dir_name = module_id.split(".")[0]
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    backend_mod_dir = project_root / "backend" / "modules" / root_dir_name

    if not backend_mod_dir.exists() or not backend_mod_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(request, "MODULE_DIR_NOT_FOUND", "module_dir_not_found"),
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Файлы бэкенда: backend/modules/{module_id}/...
        for file_path in backend_mod_dir.rglob("*"):
            if file_path.is_file() and "__pycache__" not in file_path.parts:
                arcname = Path("backend") / "modules" / root_dir_name / file_path.relative_to(backend_mod_dir)
                zip_file.write(file_path, arcname)

        # 2. Файлы фронтенда: frontend/src/modules/{module_id}/...
        frontend_mod_dir = project_root / "frontend" / "src" / "modules" / root_dir_name
        if frontend_mod_dir.exists() and frontend_mod_dir.is_dir():
            for file_path in frontend_mod_dir.rglob("*"):
                if file_path.is_file():
                    arcname = Path("frontend") / "src" / "modules" / root_dir_name / file_path.relative_to(frontend_mod_dir)
                    zip_file.write(file_path, arcname)

    buf.seek(0)
    filename = f"{root_dir_name}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{module_id}")
async def delete_module_endpoint(
    module_id: str,
    request: Request,
    user: CurrentUser = Depends(require_permission("modules.manage")),
) -> dict[str, Any]:
    """Удаление модуля из системы и с диска (включая бэкенд и фронтенд)."""
    manifest = get_manifest(module_id)
    if not manifest:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(request, "MODULE_NOT_FOUND", "module_not_found"),
        )

    if manifest.type == "system":
        raise HTTPException(
            status_code=400,
            detail=make_error_detail(request, "MODULE_CANNOT_DELETE_SYSTEM", "module_cannot_delete_system"),
        )

    unload_single_module(module_id)
    unregister_manifest(module_id)

    root_dir_name = module_id.split(".")[0]
    project_root = Path(__file__).resolve().parent.parent.parent.parent

    # 1. Удаление директории бэкенда модуля: backend/modules/{module_id}/
    backend_mod_dir = project_root / "backend" / "modules" / root_dir_name
    if backend_mod_dir.exists() and backend_mod_dir.is_dir():
        try:
            shutil.rmtree(backend_mod_dir)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=make_error_detail(request, "MODULE_DELETE_ERROR", "module_delete_error", exc=str(exc)),
            )

    # 2. Удаление директории фронтенда модуля: frontend/src/modules/{module_id}/
    frontend_mod_dir = project_root / "frontend" / "src" / "modules" / root_dir_name
    if frontend_mod_dir.exists() and frontend_mod_dir.is_dir():
        try:
            shutil.rmtree(frontend_mod_dir)
        except Exception as exc:
            _log.warning(f"Failed to remove frontend module directory {frontend_mod_dir}: {exc}")

    return {"ok": True, "module_id": module_id}


@router.get("/config-schema")
async def module_config_schema(
    user: CurrentUser = Depends(require_permission("modules.view")),
) -> dict[str, Any]:
    """Схема enable/disable для UI."""
    return get_module_enable_config_schema()


@router.put("/{module_id}/enabled")
async def toggle_module(
    module_id: str,
    body: EnableBody,
    request: Request,
    user: CurrentUser = Depends(require_permission("modules.manage")),
) -> dict[str, Any]:
    """Включить/выключить модуль."""
    state = set_module_enabled(module_id, body.enabled)
    manifest = get_manifest(module_id)
    if manifest:
        if body.enabled:
            modules_dir = Path(__file__).resolve().parent.parent.parent / "modules"
            _load_single_manifest(manifest, request.app, modules_dir)
        else:
            unload_single_module(module_id)
    return {"module_id": module_id, "enabled": body.enabled, "state": state}


@router.get("/{module_id}/views")
async def module_views(
    module_id: str,
    user: CurrentUser = Depends(require_permission("modules.view")),
) -> dict[str, Any]:
    """UI-маршруты модуля."""
    views = get_module_views(module_id)
    return {"items": views}


@router.get("/{module_id}/settings-definition")
async def module_settings_definition(
    module_id: str,
    request: Request = None,
    user: CurrentUser = Depends(require_permission("settings.view")),
) -> dict[str, Any]:
    """JSON Schema настроек модуля + defaults."""
    definition = get_module_settings_definition(module_id)
    if definition is None:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(request, "MODULE_NO_SETTINGS_SCHEMA", "module_no_settings_schema"),
        )
    return definition


@router.get("/{module_id}/settings")
async def module_settings_get(
    module_id: str,
    user: CurrentUser = Depends(require_permission("settings.view")),
) -> dict[str, Any]:
    """Текущие настройки модуля."""
    return get_module_settings(module_id)


@router.put("/{module_id}/settings")
async def module_settings_put(
    module_id: str,
    body: dict[str, Any],
    user: CurrentUser = Depends(require_permission("settings.edit")),
) -> dict[str, Any]:
    """Сохранить настройки модуля."""
    save_module_settings(module_id, body)
    return {"ok": True, "module_id": module_id}


@router.get("/{module_id}/status")
async def module_status(module_id: str, request: Request = None) -> dict[str, Any]:
    """Текущее состояние модуля (из get_status())."""
    instance = get_instance(module_id)
    if instance is None:
        raise HTTPException(
            status_code=404,
            detail=make_error_detail(request, "MODULE_NOT_LOADED", "module_not_loaded"),
        )
    if not hasattr(instance, "get_status"):
        return {"module_id": module_id, "status": "running", "detail": tr(request, "module_no_status_method")}
    try:
        status = instance.get_status()
        return {"module_id": module_id, **status}
    except Exception as exc:
        return {"module_id": module_id, "status": "error", "detail": str(exc)}


@router.get("/{module_id}/locales/{lang}")
async def module_locales(module_id: str, lang: str) -> dict[str, Any]:
    """Словарь локализации для конкретного модуля и языка."""
    manifest = get_manifest(module_id)
    result = {}
    if manifest and manifest.i18n and lang in manifest.i18n:
        result.update(manifest.i18n[lang])

    modules_dir = Path(__file__).resolve().parent.parent.parent / "modules"
    module_path = modules_dir / module_id.split(".")[0]
    json_path = module_path / "locales" / f"{lang}.json"

    if json_path.is_file():
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    result.update(data)
        except Exception:
            pass

    return {"module_id": module_id, "lang": lang, "messages": result}


