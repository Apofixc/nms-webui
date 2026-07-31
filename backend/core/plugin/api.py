import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel

from backend.core.auth import CurrentUser, require_permission
from backend.core.i18n import tr
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
    """Загрузка и установка модуля из ZIP-архива."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail=tr(request, "Файл должен быть ZIP архивом", "File must be a ZIP archive"),
        )

    modules_dir = Path(__file__).resolve().parent.parent.parent / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(file.file, "r") as zip_ref:
            manifest_file = next((name for name in zip_ref.namelist() if name.endswith("manifest.yaml") or name.endswith("manifest.yml")), None)
            if not manifest_file:
                raise HTTPException(
                    status_code=400,
                    detail=tr(request, "В архиве отсутствует manifest.yaml", "manifest.yaml is missing in archive"),
                )

            # Чтение манифеста для определения module_id
            import yaml
            manifest_data = yaml.safe_load(zip_ref.read(manifest_file))
            if not isinstance(manifest_data, dict) or not manifest_data.get("id"):
                raise HTTPException(
                    status_code=400,
                    detail=tr(request, "Невалидный manifest.yaml в архиве", "Invalid manifest.yaml in archive"),
                )

            module_id = str(manifest_data["id"]).split(".")[0]
            target_dir = modules_dir / module_id

            # Проверка ZipSlip безопасности
            for member in zip_ref.infolist():
                extracted_path = (target_dir / member.filename).resolve()
                if not str(extracted_path).startswith(str(target_dir.resolve())):
                    raise HTTPException(
                        status_code=400,
                        detail=tr(request, "Небезопасный путь в архиве (ZipSlip)", "Unsafe file path in archive"),
                    )

            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Распаковка архива во временную/целевую директорию модуля
            zip_ref.extractall(target_dir)

            # 1. Обработка бэкенд файлов
            backend_in_zip = target_dir / "backend"
            if backend_in_zip.exists() and backend_in_zip.is_dir():
                backend_mod_dir = backend_in_zip / "modules" / module_id
                source_dir = backend_mod_dir if backend_mod_dir.exists() else backend_in_zip
                
                for item in source_dir.iterdir():
                    dest = target_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.move(str(item), str(dest))
                shutil.rmtree(backend_in_zip)

            # 2. Обработка фронтенд файлов
            frontend_in_zip = target_dir / "frontend"
            if frontend_in_zip.exists() and frontend_in_zip.is_dir():
                project_root = Path(__file__).resolve().parent.parent.parent.parent
                frontend_src = project_root / "frontend" / "src"
                
                # Поддержка frontend/src/modules и frontend/modules
                zip_src = frontend_in_zip / "src" if (frontend_in_zip / "src").exists() else frontend_in_zip
                
                zip_mod_ui = zip_src / "modules"
                if zip_mod_ui.exists():
                    shutil.copytree(zip_mod_ui, frontend_src / "modules", dirs_exist_ok=True)
                    
                zip_views_ui = zip_src / "views"
                if zip_views_ui.exists():
                    shutil.copytree(zip_views_ui, frontend_src / "views", dirs_exist_ok=True)
                    
                shutil.rmtree(frontend_in_zip)

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
            detail=tr(request, f"Ошибка установки модуля: {exc}", f"Failed to install module: {exc}"),
        )


@router.get("/{module_id}/export")
async def export_module_endpoint(
    module_id: str,
    request: Request,
    user: CurrentUser = Depends(require_permission("modules.view")),
) -> Response:
    """Упаковка модуля в ZIP-архив и скачивание."""
    import io
    manifest = get_manifest(module_id)
    if not manifest:
        raise HTTPException(
            status_code=404,
            detail=tr(request, "Модуль не найден", "Module not found"),
        )

    root_dir_name = module_id.split(".")[0]
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    modules_dir = project_root / "backend" / "modules"
    target_dir = modules_dir / root_dir_name

    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=tr(request, "Папка модуля не найдена на диске", "Module directory not found on disk"),
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Упаковка бэкенд файлов с точным путем backend/modules/{module_id}/...
        for file_path in target_dir.rglob("*"):
            if file_path.is_file() and "__pycache__" not in file_path.parts:
                arcname = Path("backend") / "modules" / root_dir_name / file_path.relative_to(target_dir)
                zip_file.write(file_path, arcname)

        # 2. Упаковка фронтенд файлов с точным путем frontend/src/modules/{module_id}/...
        frontend_src = project_root / "frontend" / "src"
        frontend_mod_dir = frontend_src / "modules" / root_dir_name
        if frontend_mod_dir.exists() and frontend_mod_dir.is_dir():
            for file_path in frontend_mod_dir.rglob("*"):
                if file_path.is_file():
                    arcname = Path("frontend") / "src" / "modules" / root_dir_name / file_path.relative_to(frontend_mod_dir)
                    zip_file.write(file_path, arcname)

        pascal_name = "".join(word.capitalize() for word in root_dir_name.replace("-", "_").split("_"))
        possible_views = [
            f"{pascal_name}View.vue",
            f"{pascal_name}.vue",
            f"{root_dir_name}View.vue",
            f"{root_dir_name}.vue",
            f"{root_dir_name}-view.vue",
        ]
        views_dir = frontend_src / "views"
        if views_dir.exists():
            for view_name in possible_views:
                view_path = views_dir / view_name
                if view_path.exists() and view_path.is_file():
                    arcname = Path("frontend") / "src" / "views" / view_name
                    zip_file.write(view_path, arcname)

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
            detail=tr(request, "Модуль не найден", "Module not found"),
        )

    if manifest.type == "system":
        raise HTTPException(
            status_code=400,
            detail=tr(request, "Системные модули не могут быть удалены", "System modules cannot be deleted"),
        )

    unload_single_module(module_id)
    unregister_manifest(module_id)

    root_dir_name = module_id.split(".")[0]
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    modules_dir = project_root / "backend" / "modules"
    target_dir = modules_dir / root_dir_name

    # 1. Удаление папки модуля из backend
    if target_dir.exists() and target_dir.is_dir():
        try:
            shutil.rmtree(target_dir)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=tr(request, f"Не удалось удалить файлы модуля: {exc}", f"Failed to remove module files: {exc}"),
            )

    # 2. Очистка фронтенд файлов модуля (в frontend/src/modules/ и frontend/src/views/)
    frontend_src = project_root / "frontend" / "src"
    frontend_mod_dir = frontend_src / "modules" / root_dir_name
    if frontend_mod_dir.exists() and frontend_mod_dir.is_dir():
        try:
            shutil.rmtree(frontend_mod_dir)
        except Exception as exc:
            _log.warning(f"Failed to remove frontend module directory {frontend_mod_dir}: {exc}")

    possible_views = set()
    pascal_name = "".join(word.capitalize() for word in root_dir_name.replace("-", "_").split("_"))
    possible_views.update([
        f"{pascal_name}View.vue",
        f"{pascal_name}.vue",
        f"{root_dir_name}View.vue",
        f"{root_dir_name}.vue",
        f"{root_dir_name}-view.vue",
    ])

    if manifest and manifest.routes:
        for r in manifest.routes:
            if r.name:
                r_pascal = "".join(word.capitalize() for word in r.name.replace("-", "_").split("_"))
                possible_views.update([
                    f"{r_pascal}.vue",
                    f"{r_pascal}View.vue",
                    f"{r.name}.vue",
                ])

    views_dir = frontend_src / "views"
    if views_dir.exists():
        for view_name in possible_views:
            view_path = views_dir / view_name
            if view_path.exists() and view_path.is_file():
                try:
                    view_path.unlink()
                except Exception as exc:
                    _log.warning(f"Failed to remove frontend view file {view_path}: {exc}")

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
            detail=tr(request, "Нет схемы настроек для этого модуля", "No settings schema for this module"),
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
            detail=tr(request, "Модуль не загружен или не имеет инстанса", "Module not loaded or has no instance"),
        )
    if not hasattr(instance, "get_status"):
        return {"module_id": module_id, "status": "running", "detail": "no get_status() method"}
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


