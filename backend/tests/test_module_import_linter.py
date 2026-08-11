"""Тесты для скрипта линтера импортов модулей check_module_imports.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.check_module_imports import check_module_file


def test_import_linter_script_runs():
    """Проверка работы всей утилиты check_module_imports.py."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    script_path = repo_root / "scripts" / "check_module_imports.py"

    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Linter script failed: {res.stdout}\n{res.stderr}"
    assert "comply with core & module import rules" in res.stdout


def test_import_linter_ast_checks(tmp_path: Path):
    """Проверка работы AST-проверок линтера на корректных и некорректных ситуациях."""
    modules_root = tmp_path / "backend" / "modules"
    mod_a_dir = modules_root / "mod_a"
    mod_a_dir.mkdir(parents=True)

    # 1. Корректные импорты
    valid_py = mod_a_dir / "valid.py"
    valid_py.write_text(
        """from backend.core.public import BaseModule, ModuleContext
from backend.core.auth import CurrentUser
from backend.core.exceptions import NMSError
""",
        encoding="utf-8",
    )

    errors = check_module_file(valid_py, modules_root)
    assert len(errors) == 0

    # 2. Некорректный прямой импорт ядра
    invalid_core_py = mod_a_dir / "invalid_core.py"
    invalid_core_py.write_text(
        """from backend.core.events import broadcaster
from backend.core.database import get_system_setting
""",
        encoding="utf-8",
    )

    errors = check_module_file(invalid_core_py, modules_root)
    assert len(errors) == 2
    assert any("Forbidden import from 'backend.core.events'" in e for e in errors)
    assert any("Forbidden import from 'backend.core.database'" in e for e in errors)

    # 3. Некорректный межмодульный импорт без объявления в манифесте
    invalid_mod_py = mod_a_dir / "invalid_mod.py"
    invalid_mod_py.write_text(
        """from backend.modules.mod_b.contract import SomeDTO
""",
        encoding="utf-8",
    )

    errors = check_module_file(invalid_mod_py, modules_root)
    assert len(errors) == 1
    assert "not listed in manifest deps/optional_deps" in errors[0]
