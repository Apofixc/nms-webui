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
            
            # Если файлы лежат в подпапке архива, извлекаем с сохранением структуры
            zip_ref.extractall(target_dir)

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
    modules_dir = Path(__file__).resolve().parent.parent.parent / "modules"
    target_dir = modules_dir / root_dir_name

    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=tr(request, "Папка модуля не найдена на диске", "Module directory not found on disk"),
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in target_dir.rglob("*"):
            if file_path.is_file() and "__pycache__" not in file_path.parts:
                arcname = file_path.relative_to(target_dir)
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
    """Удаление модуля из системы и с диска."""
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
    modules_dir = Path(__file__).resolve().parent.parent.parent / "modules"
    target_dir = modules_dir / root_dir_name

    if target_dir.exists() and target_dir.is_dir():
        try:
            shutil.rmtree(target_dir)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=tr(request, f"Не удалось удалить файлы модуля: {exc}", f"Failed to remove module files: {exc}"),
            )

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


