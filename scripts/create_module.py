#!/usr/bin/env python3
"""CLI-скрипт генерации структуры нового модуля платформы NMS-WebUI.

Создает необходимые файлы бэкенда (Python, YAML, JSON) и фронтенда (Vue) по стандартам платформы.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def to_pascal_case(snake_str: str) -> str:
    """Преобразует snake_case строку в PascalCase."""
    return "".join(word.capitalize() for word in snake_str.split("_"))


def to_camel_case(snake_str: str) -> str:
    """Преобразует snake_case строку в camelCase."""
    words = snake_str.split("_")
    return words[0] + "".join(w.capitalize() for w in words[1:])


def create_module(
    module_id: str,
    name: str | None = None,
    description: str | None = None,
    base_dir: Path | None = None,
    force: bool = False,
) -> bool:
    """Генерирует файлы нового модуля."""
    if not re.match(r"^[a-z][a-z0-9_]*$", module_id):
        print(f"❌ Ошибка: Идентификатор модуля '{module_id}' должен быть в snake_case (начинаться с латинской буквы, содержать только строчные буквы, цифры и знаки подчеркивания).")
        return False

    root_dir = base_dir or Path(__file__).resolve().parent.parent
    backend_module_dir = root_dir / "backend" / "modules" / module_id
    frontend_module_dir = root_dir / "frontend" / "src" / "modules" / module_id

    if backend_module_dir.exists() and not force:
        print(f"❌ Ошибка: Директория бэкенда '{backend_module_dir}' уже существует. Используйте --force для перезаписи.")
        return False

    pascal_name = to_pascal_case(module_id)
    camel_id = to_camel_case(module_id)
    title_key = f"{camel_id}Title"
    desc_key = f"{camel_id}Desc"
    disp_name = name or pascal_name
    disp_desc = description or f"Модуль {disp_name}"

    # Создание директорий
    locales_dir = backend_module_dir / "locales"
    tests_dir = backend_module_dir / "tests"
    locales_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)
    frontend_module_dir.mkdir(parents=True, exist_ok=True)

    # 1. manifest.yaml
    manifest_content = f"""id: {module_id}
name: {title_key}
version: 1.0.0
description: {desc_key}
enabled_by_default: true
type: feature

entrypoints:
  factory: "backend.modules.{module_id}:create_module"
  router: "backend.modules.{module_id}.api:get_router"

routes:
  - path: "/{module_id.replace('_', '-')}"
    name: "{module_id.replace('_', '-')}-index"
    meta:
      title: "{disp_name}"
      titleKey: "{title_key}"
      icon: "extension"
      requires_auth: true
      permissions:
        - "module.{module_id}.view"

menu:
  location: sidebar
  group: "main"
  items:
    - path: "/{module_id.replace('_', '-')}"
      label: "{title_key}"
      icon: "extension"

permissions:
  - id: "module.{module_id}.view"
    name: "Просмотр модуля {disp_name}"
    category: "{disp_name}"
    description: "Разрешает доступ к модулю {disp_name}"
"""
    (backend_module_dir / "manifest.yaml").write_text(manifest_content, encoding="utf-8")

    # 2. __init__.py
    doc_init = f'"""Точка входа модуля {module_id}."""'
    init_content = f"""{doc_init}
from __future__ import annotations

from backend.core.plugin.context import ModuleContext
from .module import {pascal_name}Module


def create_module(ctx: ModuleContext) -> {pascal_name}Module:
    \"\"\"Фабрика инициализации модуля.\"\"\"
    return {pascal_name}Module(ctx)
"""
    (backend_module_dir / "__init__.py").write_text(init_content, encoding="utf-8")

    # 3. module.py
    doc_mod = f'"""Класс управления жизненным циклом модуля {module_id}."""'
    module_content = f"""{doc_mod}
from __future__ import annotations

import logging
from typing import Any

from backend.core.plugin.context import ModuleContext
from backend.modules.base import BaseModule

_log = logging.getLogger("nms.module.{module_id}")


class {pascal_name}Module(BaseModule):
    \"\"\"Бизнес-логика и управление жизненным циклом модуля {disp_name}.\"\"\"

    def __init__(self, context: ModuleContext):
        super().__init__(context)

    def init(self) -> None:
        \"\"\"Инициализация ресурсов при старте системы.\"\"\"
        _log.info("Инициализация модуля %s", self.context.module_id)

    def start(self) -> None:
        \"\"\"Запуск фоновых задач модуля.\"\"\"
        _log.info("Запуск модуля %s", self.context.module_id)

    async def stop(self) -> None:
        \"\"\"Остановка ресурсов модуля.\"\"\"
        _log.info("Остановка модуля %s", self.context.module_id)

    def get_status(self) -> dict[str, Any]:
        \"\"\"Возврат текущего статуса модуля.\"\"\"
        return {{
            "status": "ok",
            "module_id": self.context.module_id,
            "version": self.context.manifest.version,
        }}
"""
    (backend_module_dir / "module.py").write_text(module_content, encoding="utf-8")

    # 4. api.py
    doc_api = f'"""FastAPI роутер модуля {module_id}."""'
    api_content = f"""{doc_api}
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth import CurrentUser, require_permission

router = APIRouter()


@router.get("/status")
async def get_status(
    user: CurrentUser = Depends(require_permission("module.{module_id}.view")),
):
    \"\"\"Возвращает статус модуля.\"\"\"
    return {{
        "status": "ok",
        "module_id": "{module_id}",
        "user": user.username,
    }}


def get_router() -> APIRouter:
    \"\"\"Возвращает инстанс APIRouter модуля.\"\"\"
    return router
"""
    (backend_module_dir / "api.py").write_text(api_content, encoding="utf-8")

    # 5. locales/ru.json & locales/en.json
    ru_json = f"""{{
  "messages": {{
    "{title_key}": "{disp_name}",
    "{desc_key}": "{disp_desc}"
  }}
}}
"""
    en_json = f"""{{
  "messages": {{
    "{title_key}": "{disp_name}",
    "{desc_key}": "{disp_desc}"
  }}
}}
"""
    (locales_dir / "ru.json").write_text(ru_json, encoding="utf-8")
    (locales_dir / "en.json").write_text(en_json, encoding="utf-8")

    # 6. Frontend Vue component
    vue_filename = f"{pascal_name}View.vue"
    vue_content = f"""<template>
  <div class="p-6 space-y-4">
    <div class="flex items-center space-x-3">
      <span class="material-symbols-outlined text-primary text-3xl">extension</span>
      <div>
        <h1 class="text-2xl font-bold">{{{{ t('{title_key}') }}}}</h1>
        <p class="text-sm text-on-surface-variant">{{{{ t('{desc_key}') }}}}</p>
      </div>
    </div>

    <div class="p-4 rounded-lg bg-surface-container border border-outline-variant">
      <p class="text-sm font-medium">Статус API модуля:</p>
      <pre class="mt-2 p-3 rounded bg-surface-container-high font-mono text-xs">{{{{ apiData }}}}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import {{ ref, onMounted }} from 'vue'
import {{ useI18n }} from '@/core/i18n'
import api from '@/core/api'

const {{ t }} = useI18n()
const apiData = ref<any>('Загрузка...')

onMounted(async () => {{
  try {{
    const res = await api.get('/api/v1/m/{module_id}/status')
    apiData.value = res.data
  }} catch (err) {{
    apiData.value = {{ error: String(err) }}
  }}
}})
</script>
"""
    (frontend_module_dir / vue_filename).write_text(vue_content, encoding="utf-8")

    # 7. Unit test
    doc_test = f'"""Автотест модуля {module_id}."""'
    test_content = f"""{doc_test}
from __future__ import annotations

import pytest
from backend.core.plugin.manifest import ModuleManifest
from backend.modules.{module_id}.module import {pascal_name}Module


def test_{module_id}_manifest():
    manifest = ModuleManifest(
        id="{module_id}",
        name="{title_key}",
        version="1.0.0",
        description="{desc_key}",
    )
    assert manifest.id == "{module_id}"
"""
    (tests_dir / f"test_{module_id}.py").write_text(test_content, encoding="utf-8")

    print(f"✅ Модуль '{module_id}' успешно создан!")
    print(f"   - Бэкенд: {backend_module_dir}")
    print(f"   - Фронтенд: {frontend_module_dir / vue_filename}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Скаффолдинг нового модуля NMS-WebUI")
    parser.add_argument("--id", required=True, help="Идентификатор модуля в snake_case (например: my_plugin)")
    parser.add_argument("--name", help="Отображаемое имя модуля (например: Мой Плагин)")
    parser.add_argument("--description", help="Описание модуля")
    parser.add_argument("--force", action="store_true", help="Перезаписать существующий модуль")

    args = parser.parse_args()
    success = create_module(
        module_id=args.id,
        name=args.name,
        description=args.description,
        force=args.force,
    )
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
