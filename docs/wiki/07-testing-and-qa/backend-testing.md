# Тестирование Backend (Pytest)

Для тестирования серверной части NMS WebUI используется фреймворк **Pytest** и клиент тестирования FastAPI (`TestClient`).

---

## 🚀 Запуск тестов

Тесты backend расположены в директории `tests/`. Запуск выполняется через виртуальное окружение Python:

```bash
# Запуск всех тестов backend
pytest

# Запуск с отображением подробного вывода
pytest -v

# Запуск конкретного тестового файла
pytest tests/test_auth_users_audit.py

# Запуск конкретного теста по имени
pytest -k "test_user_login_success"
```

 Конфигурационный файл [pytest.ini](file:///opt/nms-webui/pytest.ini) устанавливает `pythonpath = .`, что позволяет импортировать модули через `from backend.core...`.

---

## 🧪 Структура и Категории Тестов

1. **Безопасность и Аутентификация** (`test_auth_users_audit.py`, `test_security_edge_cases.py`):
   - Генерация JWT токенов авторизации.
   - Проверка хэширования паролей (`argon2` / `bcrypt`).
   - Изоляция ролей и пермишенов (RBAC).
   - Двухфакторная аутентификация (MFA/TOTP).
2. **Управление Пользователями и Сессиями** (`test_sessions_and_status.py`, `test_users_management_suite.py`):
   - Отзыв JWT-токенов при выходе или админском сбросе сессий.
   - Блокировка учетных записей при превышении попыток входа.
3. **Модули и Виджеты** (`test_tuya_module.py`, `test_widgets.py`):
   - Валидация манифестов `manifest.yaml`.
   - Проверка возвращаемых структурах API для виджетов дашборда.
4. **Логирование** (`test_log_providers.py`, `test_remote_log_manager.py`):
   - Чтение и фильтрация логов.

---

## 🛠️ Написание тестов с моками

Для изоляции тестов от реальной SQLite базы данных используется мокирование с временными базами данных или фикстурами в памяти.

### Пример теста эндпоинта FastAPI:
```python
import pytest
from fastapi.testclient import TestClient
from backend.core.app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert "database" in data
```
