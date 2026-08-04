"""Тестовая проверка топологической сортировки и контекста для необязательных зависимостей."""
import sys
from pathlib import Path

# Добавляем корень проекта в pythonpath
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.core.plugin.manifest import ModuleManifest
from backend.core.plugin.resolver import toposort_modules
from backend.core.plugin.context import ModuleContext
from backend.core.plugin.registry import register_manifest, is_module_active


def test_toposort_optional_deps():
    """Модуль B опционально зависит от A. При наличии обоих A закружается до B."""
    mod_a = ModuleManifest(id="mod_a", name="Module A")
    mod_b = ModuleManifest(id="mod_b", name="Module B", optional_deps=["mod_a"])

    order = toposort_modules([mod_b, mod_a])
    ids = [m.id for m in order]
    assert ids == ["mod_a", "mod_b"], f"Expected ['mod_a', 'mod_b'], got {ids}"
    print("✓ Toposort optional dependencies test passed")


def test_toposort_missing_optional_deps():
    """Модуль B опционально зависит от несуществующего C. Загрузка происходит без ошибок."""
    mod_b = ModuleManifest(id="mod_b", name="Module B", optional_deps=["mod_missing"])

    order = toposort_modules([mod_b])
    ids = [m.id for m in order]
    assert ids == ["mod_b"], f"Expected ['mod_b'], got {ids}"
    print("✓ Missing optional dependency does not block loading")


def test_context_dependency_checks():
    """Проверка работы методов has_dependency и is_module_active в ModuleContext."""
    mod_a = ModuleManifest(id="mod_a", name="Module A", enabled_by_default=True)
    register_manifest(mod_a, enabled=True)

    ctx = ModuleContext(module_id="mod_b", root=Path("."))
    assert ctx.has_dependency("mod_a") is True, "mod_a must be reported as active"
    assert ctx.has_dependency("mod_non_existent") is False, "non-existent module must be reported as inactive"
    print("✓ ModuleContext dependency check methods test passed")


if __name__ == "__main__":
    test_toposort_optional_deps()
    test_toposort_missing_optional_deps()
    test_context_dependency_checks()
    print("\nAll optional dependencies tests PASSED successfully!")
