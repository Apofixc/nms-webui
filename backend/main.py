"""NMS-WebUI — точка входа.

Запуск: uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload
"""
from backend.core.app import create_app

app = create_app()
