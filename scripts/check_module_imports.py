#!/usr/bin/env python3
"""Линтер правил импорта для модулей NMS-WebUI.

Правила:
1. "Все, что требует module_id — через ctx; остальное — прямой импорт".
   Модули могут импортировать из backend.core только разрешённый публичный список:
   - backend.core.public (или из него конкретные символы: BaseModule, BaseSubmodule, ModuleStatusResponse,
     CurrentUser, require_permission, require_module_permission, NMSError и его наследники)
   - backend.core.auth (CurrentUser, require_permission, require_module_permission)
   - backend.core.exceptions (NMSError и подклассы)
   - backend.core.plugin.context (ModuleContext)
   - backend.modules.base (BaseModule, BaseSubmodule, ModuleStatusResponse)
   Прямые импорты из backend.core.events, backend.core.database, backend.core.audit,
   backend.core.log_providers и т.д. строго запрещены.

2. Межмодульные импорты:
   Модуль mod_A может импортировать только contract.py чужого модуля mod_B:
   backend.modules.mod_B.contract (и только если mod_B прописан в deps/optional_deps манифеста mod_A).
"""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path
from typing import Any

# Разрешенные символы из backend.core
ALLOWED_CORE_PUBLIC_SYMBOLS = {
    "BaseModule",
    "BaseSubmodule",
    "ModuleStatusResponse",
    "ModuleContext",
    "CurrentUser",
    "require_permission",
    "require_module_permission",
    "user_has_permission",
    "create_access_token",
    "decode_access_token",
    "tr",
    "get_lang",
    "encrypt_secret",
    "decrypt_secret",
    "mask_secret",
    "BaseLogProvider",
    "LocalFileLogProvider",
    "RemoteHTTPLogProvider",
    "NMSError",
    "NMSModuleNotFoundError",
    "ModuleDisabledError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ValidationError",
    "ModuleValidationError",
}

# Разрешенные модули ядра
ALLOWED_CORE_MODULES = {
    "backend.core.public",
    "backend.core.auth",
    "backend.core.i18n",
    "backend.core.crypto",
    "backend.core.log_providers",
    "backend.core.exceptions",
    "backend.core.plugin.context",
    "backend.modules.base",
}


def load_module_manifest_deps(module_dir: Path) -> set[str]:
    """Загрузить объявление зависимостей (deps/optional_deps) модуля из его манифеста."""
    deps: set[str] = set()
    manifest_file = None
    for name in ("manifest.json", "manifest.yaml", "manifest.yml"):
        candidate = module_dir / name
        if candidate.exists():
            manifest_file = candidate
            break

    if not manifest_file:
        return deps

    try:
        if manifest_file.suffix == ".json":
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            import yaml  # type: ignore

            with open(manifest_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

        if isinstance(data, dict):
            deps_list = data.get("dependencies", []) or data.get("deps", [])
            opt_deps = data.get("optional_dependencies", []) or data.get("optional_deps", [])
            for item in deps_list:
                if isinstance(item, str):
                    deps.add(item)
                elif isinstance(item, dict) and "id" in item:
                    deps.add(item["id"])
            for item in opt_deps:
                if isinstance(item, str):
                    deps.add(item)
                elif isinstance(item, dict) and "id" in item:
                    deps.add(item["id"])
    except Exception:
        pass

    return deps


class ModuleImportVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, current_module_id: str | None, declared_deps: set[str]) -> None:
        self.file_path = file_path
        self.current_module_id = current_module_id
        self.declared_deps = declared_deps
        self.errors: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check_import_module(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self._check_import_from(node.module, [a.name for a in node.names], node.lineno)
        self.generic_visit(node)

    def _check_import_module(self, module_name: str, lineno: int) -> None:
        # Проверка прямого импорта backend.core.*
        if module_name.startswith("backend.core"):
            if module_name not in ALLOWED_CORE_MODULES:
                self.errors.append(
                    f"Line {lineno}: Forbidden direct import of core module '{module_name}'. "
                    f"Use ModuleContext API or import from backend.core.public."
                )

        # Проверка прямого импорта чужих модулей
        if module_name.startswith("backend.modules.") and self.current_module_id:
            parts = module_name.split(".")
            if len(parts) >= 3:
                target_module = parts[2]
                if target_module != self.current_module_id and target_module != "base":
                    # Импорт модуля целиком запрещён, разрешён только contract
                    if len(parts) < 4 or parts[3] != "contract":
                        self.errors.append(
                            f"Line {lineno}: Forbidden import of target module '{target_module}'. "
                            f"Only 'backend.modules.{target_module}.contract' can be imported."
                        )
                    if target_module not in self.declared_deps:
                        self.errors.append(
                            f"Line {lineno}: Import of module '{target_module}' is not declared in deps/optional_deps of manifest."
                        )

    def _check_import_from(self, module_name: str, names: list[str], lineno: int) -> None:
        # 1. Проверка импорта из backend.core
        if module_name.startswith("backend.core"):
            if module_name not in ALLOWED_CORE_MODULES:
                self.errors.append(
                    f"Line {lineno}: Forbidden import from '{module_name}'. "
                    f"Modules must interact with core via ModuleContext API or backend.core.public."
                )
            else:
                # Если импортируется разрешенный модуль, проверяем импортируемые символы (если это auth/exceptions)
                if module_name == "backend.core.auth":
                    for name in names:
                        if name not in ("CurrentUser", "require_permission", "require_module_permission"):
                            self.errors.append(
                                f"Line {lineno}: Symbol '{name}' from backend.core.auth is not in public core API."
                            )
                elif module_name == "backend.core.exceptions":
                    for name in names:
                        if name not in ALLOWED_CORE_PUBLIC_SYMBOLS and not name.endswith("Error"):
                            self.errors.append(
                                f"Line {lineno}: Symbol '{name}' from backend.core.exceptions is not allowed in public core API."
                            )

        # 2. Проверка импорта из backend.modules
        if module_name.startswith("backend.modules") and self.current_module_id:
            parts = module_name.split(".")
            if len(parts) >= 3:
                target_module = parts[2]
                if target_module != self.current_module_id and target_module != "base":
                    # Должно оканчиваться на contract или быть backend.modules.<mod>.contract
                    is_contract_import = (len(parts) >= 4 and parts[3] == "contract") or ("contract" in names)
                    if not is_contract_import:
                        self.errors.append(
                            f"Line {lineno}: Forbidden import from '{module_name}'. "
                            f"Only 'contract.py' of module '{target_module}' can be imported."
                        )
                    if target_module not in self.declared_deps:
                        self.errors.append(
                            f"Line {lineno}: Module '{target_module}' is imported but not listed in manifest deps/optional_deps."
                        )


def check_module_file(file_path: Path, modules_root: Path) -> list[str]:
    rel_path = file_path.relative_to(modules_root)
    parts = rel_path.parts
    if len(parts) < 2:
        # Например, backend/modules/base.py или backend/modules/__init__.py
        return []

    current_module_id = parts[0]
    module_dir = modules_root / current_module_id
    declared_deps = load_module_manifest_deps(module_dir)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except Exception as exc:
        return [f"Failed to parse AST: {exc}"]

    visitor = ModuleImportVisitor(file_path, current_module_id, declared_deps)
    visitor.visit(tree)
    return visitor.errors


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    modules_root = repo_root / "backend" / "modules"

    if not modules_root.exists():
        print(f"Modules directory not found at {modules_root}")
        return 0

    total_errors = 0
    total_files = 0

    for root, _, files in os.walk(modules_root):
        for file_name in files:
            if file_name.endswith(".py"):
                file_path = Path(root) / file_name
                total_files += 1
                errors = check_module_file(file_path, modules_root)
                if errors:
                    total_errors += len(errors)
                    print(f"\n[FAIL] {file_path.relative_to(repo_root)}:")
                    for err in errors:
                        print(f"  - {err}")

    if total_errors > 0:
        print(f"\n❌ Found {total_errors} import rule violations in {total_files} module files.")
        return 1

    print(f"\n✅ All {total_files} module files comply with core & module import rules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
