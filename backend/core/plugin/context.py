"""ModuleContext — минимальный контекст для инициализации модулей."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModuleContext:
    """Контекст, передаваемый модулю при инициализации.

    Содержит всё, что нужно модулю для регистрации роутеров,
    сервисов и доступа к своей конфигурации и изолированному хранилищу.
    """
    module_id: str
    root: Path
    manifest: dict[str, Any] = field(default_factory=dict)
    parent_module_id: str | None = None
    is_submodule: bool = False

    def get_data_dir(self) -> Path:
        """Получить путь к изолированной директории данных модуля."""
        clean_id = self.module_id.replace("/", "_").replace("\\", "_")
        # backend/data/modules/<module_id>/
        project_root = self.root.resolve().parent.parent.parent
        data_dir = project_root / "backend" / "data" / "modules" / clean_id
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def get_cache_dir(self) -> Path:
        """Получить путь к изолированной директории кэша модуля."""
        clean_id = self.module_id.replace("/", "_").replace("\\", "_")
        # backend/cache/modules/<module_id>/
        project_root = self.root.resolve().parent.parent.parent
        cache_dir = project_root / "backend" / "cache" / "modules" / clean_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def ensure_safe_path(self, target_path: Path | str) -> Path:
        """Проверить, что целевой путь находится строго внутри дата-директории модуля (песочница)."""
        resolved = Path(target_path).resolve()
        data_dir = self.get_data_dir().resolve()
        cache_dir = self.get_cache_dir().resolve()
        root_dir = self.root.resolve()

        if not (resolved.is_relative_to(data_dir) or resolved.is_relative_to(cache_dir) or resolved.is_relative_to(root_dir)):
            raise ValueError(f"Access denied: Path {resolved} is outside module sandbox directories.")
        return resolved

    def is_module_active(self, target_module_id: str) -> bool:
        """Проверить, зарегистрирован ли и включен ли указанный модуль."""
        from backend.core.plugin.registry import is_module_active
        return is_module_active(target_module_id)

    def has_dependency(self, target_module_id: str) -> bool:
        """Алиас для проверки наличия и активности зависимости."""
        return self.is_module_active(target_module_id)

    def get_module_instance(self, target_module_id: str) -> Any | None:
        """Получить экземпляр активного модуля (если он загружен)."""
        from backend.core.plugin.registry import get_instance
        return get_instance(target_module_id)

    def notify(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
        category: str | None = None,
        link: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Создать системное или персональное уведомление от имени текущего модуля."""
        from backend.core.notifications_api import create_notification
        return create_notification(
            title=title,
            message=message,
            notification_type=notification_type,
            category=category or self.module_id,
            link=link,
            user_id=user_id,
        )


