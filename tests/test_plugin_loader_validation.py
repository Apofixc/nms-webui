"""Тесты для проверки однослойных субмодулей и строгой валидации манифеста."""
from __future__ import annotations

from pathlib import Path
import pytest
from pydantic import ValidationError
import yaml

from backend.core.plugin.manifest import ModuleManifest
from backend.core.plugin.loader import discover_manifests, _parse_manifest
from backend.core.plugin.registry import get_module_error, clear_module_error


def test_nested_submodule_rejected(tmp_path: Path):
    """Вложенный субмодуль (папка submodules внутри субмодуля) отклоняется с ошибкой."""
    clear_module_error("parent.child")

    modules_dir = tmp_path / "modules"
    parent_dir = modules_dir / "parent"
    child_dir = parent_dir / "submodules" / "child"
    nested_dir = child_dir / "submodules" / "grandchild"

    parent_dir.mkdir(parents=True)
    child_dir.mkdir(parents=True)
    nested_dir.mkdir(parents=True)

    (parent_dir / "manifest.yaml").write_text(yaml.dump({
        "id": "parent",
        "name": "Parent Module",
        "entrypoints": {"factory": "pkg.mod:create"}
    }), encoding="utf-8")

    (child_dir / "manifest.yaml").write_text(yaml.dump({
        "id": "child",
        "name": "Child Submodule",
        "parent": "parent",
        "entrypoints": {"factory": "pkg.mod:create_sub"}
    }), encoding="utf-8")

    (nested_dir / "manifest.yaml").write_text(yaml.dump({
        "id": "grandchild",
        "name": "Nested Submodule",
        "parent": "child",
        "entrypoints": {"factory": "pkg.mod:create_nested"}
    }), encoding="utf-8")

    manifests = discover_manifests(modules_dir)

    # Родительский модуль найден
    manifest_ids = [m.id for m in manifests]
    assert "parent" in manifest_ids
    # Субмодуль child с парой submodules/ внутри не загрузился
    assert "parent.child" not in manifest_ids
    assert "parent.child.grandchild" not in manifest_ids

    # Зарегистрирована ошибка для субмодуля
    err = get_module_error("parent.child")
    assert err == "вложенные субмодули запрещены"


def test_invalid_manifest_type_i18n_entrypoints_parent(tmp_path: Path):
    """Неверный type, некорректный entrypoints, parent с точкой отклоняются."""
    # 1. Неверный type
    with pytest.raises(ValidationError):
        ModuleManifest(id="test_mod", type="invalid_type")

    # 2. Некорректный entrypoints (без двоеточия)
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(yaml.dump({
        "id": "test_mod",
        "type": "feature",
        "entrypoints": {"router": "invalid_router_path"}
    }), encoding="utf-8")

    manifest = _parse_manifest(manifest_file)
    assert manifest is None

    # 3. Parent с точкой
    with pytest.raises(ValidationError):
        ModuleManifest(id="child", parent="parent.submodule")

    # 4. Проверка отсутствия поля i18n
    valid_m = ModuleManifest(
        id="test_i18n_mod",
        entrypoints={"factory": "pkg.mod:factory_fn"}
    )
    assert not hasattr(valid_m, "i18n")
    assert "i18n" not in valid_m.to_api_dict()


def test_valid_single_layer_module_loads(tmp_path: Path):
    """Валидный однослойный модуль с субмодулем успешно сканируется."""
    modules_dir = tmp_path / "modules"
    parent_dir = modules_dir / "drivers"
    child_dir = parent_dir / "submodules" / "cisco"

    parent_dir.mkdir(parents=True)
    child_dir.mkdir(parents=True)

    (parent_dir / "manifest.yaml").write_text(yaml.dump({
        "id": "drivers",
        "name": "Network Drivers",
        "type": "system",
        "entrypoints": {"factory": "pkg.drivers:create"}
    }), encoding="utf-8")

    (child_dir / "manifest.yaml").write_text(yaml.dump({
        "id": "cisco",
        "name": "Cisco Driver",
        "type": "driver",
        "parent": "drivers",
        "entrypoints": {"factory": "pkg.drivers.cisco:create"}
    }), encoding="utf-8")

    manifests = discover_manifests(modules_dir)
    m_ids = [m.id for m in manifests]

    assert "drivers" in m_ids
    assert "drivers.cisco" in m_ids
    assert len(manifests) == 2
