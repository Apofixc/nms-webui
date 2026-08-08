"""Тест для проверки CLI-скрипт скаффолдинга модулей scripts/create_module.py."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

from scripts.create_module import create_module
from backend.core.plugin.manifest import ModuleManifest


def test_create_module_scaffolding(tmp_path: Path):
    """Проверяет корректность создания всех файлов модуля и их валидность."""
    module_id = "test_scaffold_module"
    success = create_module(
        module_id=module_id,
        name="Test Scaffold",
        description="Scaffolding test description",
        base_dir=tmp_path,
        force=True,
    )
    assert success is True

    # Проверка структуры файлов
    backend_dir = tmp_path / "backend" / "modules" / module_id
    frontend_dir = tmp_path / "frontend" / "src" / "modules" / module_id

    assert (backend_dir / "manifest.yaml").exists()
    assert (backend_dir / "__init__.py").exists()
    assert (backend_dir / "module.py").exists()
    assert (backend_dir / "api.py").exists()
    assert (backend_dir / "locales" / "ru.json").exists()
    assert (backend_dir / "locales" / "en.json").exists()
    assert (backend_dir / "tests" / f"test_{module_id}.py").exists()
    assert (frontend_dir / "TestScaffoldModuleView.vue").exists()

    # Проверка валидности сгенерированного manifest.yaml по Pydantic-модели
    import yaml
    manifest_data = yaml.safe_load((backend_dir / "manifest.yaml").read_text(encoding="utf-8"))
    manifest = ModuleManifest(**manifest_data)
    assert manifest.id == module_id
    assert manifest.name == "testScaffoldModuleTitle"

    # Проверка наличия async def stop в module.py
    module_code = (backend_dir / "module.py").read_text(encoding="utf-8")
    assert "async def stop(self) -> None:" in module_code
