"""Общие фикстуры для тестов backend."""
import pytest
from backend.core.database import init_db


@pytest.fixture(autouse=True, scope="session")
def initialized_db():
    """Гарантировать наличие схемы БД до запуска тестов."""
    init_db()
