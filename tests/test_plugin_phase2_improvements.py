"""Автотест для проверки 2-й фазы улучшений модульной системы."""
import pytest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.plugin.context import ModuleContext
from backend.core.plugin.dependencies import get_module_instance, get_module_context
from backend.core.plugin.registry import register_instance, register_manifest
from backend.core.plugin.manifest import ModuleManifest
from backend.modules.base import BaseModule, ModuleStatusResponse


@pytest.mark.anyio
async def test_async_db_methods_and_migrations(tmp_path: Path):
    """Проверка асинхронных методов БД и автомиграции колонок в ModuleContext."""
    ctx = ModuleContext(module_id="test_db_mod", root=tmp_path)
    # 0. Очистка старой тестовой таблицы при ее наличии
    await ctx.execute_sql_async("DROP TABLE IF EXISTS mod_test_db_mod_items")

    # 1. Асинхронное создание таблицы
    await ctx.create_table_async("items", {"id": "INTEGER PRIMARY KEY", "title": "TEXT"})

    # 2. Асинхронное выполнение SQL
    await ctx.execute_sql_async("INSERT INTO mod_test_db_mod_items (title) VALUES (?)", ("Test Item",))
    rows = await ctx.execute_sql_async("SELECT * FROM mod_test_db_mod_items")
    assert len(rows) == 1
    assert rows[0]["title"] == "Test Item"

    # 3. Легкая миграция: добавление колонки
    await ctx.add_column_if_not_exists("items", "description", "TEXT DEFAULT ''")
    
    # Повторная миграция не должна вызывать ошибку
    await ctx.add_column_if_not_exists("items", "description", "TEXT DEFAULT ''")

    # Проверка работы с новой колонкой
    await ctx.execute_sql_async("UPDATE mod_test_db_mod_items SET description = ? WHERE id = 1", ("Updated Desc",))
    rows_updated = await ctx.execute_sql_async("SELECT description FROM mod_test_db_mod_items WHERE id = 1")
    assert rows_updated[0]["description"] == "Updated Desc"


def test_fastapi_di_dependencies():
    """Проверка FastAPI Dependency Injection провайдеров."""
    manifest = ModuleManifest(id="di_test_mod", name="DI Test")
    register_manifest(manifest)

    class DummyModule(BaseModule):
        def init(self): pass
        def start(self): pass
        async def stop(self): pass
        def get_status(self):
            return ModuleStatusResponse(module_id="di_test_mod", details={"ok": True})

    dummy_instance = DummyModule(ModuleContext(module_id="di_test_mod", root=Path("/tmp")))
    register_instance("di_test_mod", dummy_instance)

    # Проверка получения зависимости
    dep_fn = get_module_instance("di_test_mod")
    inst = dep_fn()
    assert inst is dummy_instance

    status_resp = inst.get_status()
    assert isinstance(status_resp, ModuleStatusResponse)
    assert status_resp.module_id == "di_test_mod"

    ctx_fn = get_module_context("di_test_mod")
    ctx = ctx_fn()
    assert ctx.module_id == "di_test_mod"
