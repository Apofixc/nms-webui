"""FastAPI Dependency Injection хелперы для доступа к модулям и контекстам."""
from __future__ import annotations

from typing import Any, Callable
from backend.core.exceptions import ModuleDisabledError, NMSModuleNotFoundError
from backend.core.plugin.context import ModuleContext
from backend.core.plugin.registry import get_instance, get_manifest


def get_module_instance(module_id: str) -> Callable[[], Any]:
    """FastAPI Depends провайдер для получения экземпляра активного модуля.

    Использование:
        @router.get("/status")
        async def get_status(module: Any = Depends(get_module_instance("my_module"))):
            return module.get_status()
    """
    def _dependency() -> Any:
        instance = get_instance(module_id)
        if not instance:
            raise ModuleDisabledError(module_id)
        return instance

    return _dependency


def get_module_context(module_id: str) -> Callable[[], ModuleContext]:
    """FastAPI Depends провайдер для получения ModuleContext модуля."""
    def _dependency() -> ModuleContext:
        manifest = get_manifest(module_id)
        if not manifest:
            raise NMSModuleNotFoundError(module_id)
        from pathlib import Path
        modules_dir = Path(__file__).resolve().parent.parent.parent / "modules"
        return ModuleContext(
            module_id=module_id,
            root=modules_dir / module_id.split(".")[0],
            manifest=manifest.to_api_dict(),
        )

    return _dependency
