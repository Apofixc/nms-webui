#!/usr/bin/env python3
"""Скрипт проверки симметрии словарей локализации."""
import json
from pathlib import Path
import sys


def audit_module_locales(module_path: Path) -> bool:
    locales_dir = module_path / "locales"
    if not locales_dir.exists():
        return True

    ru_file = locales_dir / "ru.json"
    en_file = locales_dir / "en.json"

    if not ru_file.exists() or not en_file.exists():
        print(f"❌ Ошибка в {module_path.name}: отсутствуют ru.json или en.json")
        return False

    ru_keys = set(json.loads(ru_file.read_text(encoding="utf-8")).keys())
    en_keys = set(json.loads(en_file.read_text(encoding="utf-8")).keys())

    missing_in_en = ru_keys - en_keys
    missing_in_ru = en_keys - ru_keys

    if missing_in_en or missing_in_ru:
        print(f"❌ Несовпадение ключей в модуле '{module_path.name}':")
        if missing_in_en:
            print(f"   Пропущены в en.json: {missing_in_en}")
        if missing_in_ru:
            print(f"   Пропущены в ru.json: {missing_in_ru}")
        return False

    print(f"✅ Модуль '{module_path.name}': i18n ключи симметричны ({len(ru_keys)} шт.)")
    return True


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent
    modules_dir = root_dir / "backend" / "modules"
    success = True
    if modules_dir.exists():
        for mod in modules_dir.iterdir():
            if mod.is_dir():
                if not audit_module_locales(mod):
                    success = False
    if not success:
        sys.exit(1)
