# 🧪 15. Тестирование модулей и автотесты (Module QA)

Обеспечение высокого качества (Quality Assurance) модулей в **NMS WebUI** основывается на автоматизированном тестировании на всех уровнях архитектуры: от быстрых изолированных юнит-тестов бизнес-логики до интеграционной проверки REST API, хранилища данных, асинхронных сервисов и сквозных E2E-сценариев.

---

## 🧭 0. Стратегия и пирамида тестирования NMS WebUI

Разработка автотестов для модулей строится на слоистой пирамиде тестирования. Каждый слой выполняет свою задачу и гарантирует отсечение дефектов на ранних этапах:

```mermaid
flowchart TD
    E2E[7. E2E Тесты Node.js / MCP Chrome] --> FE[6. Vitest + Vue Component Tests]
    FE --> INT[3-5. REST API / Storage / WebSocket Integration]
    INT --> UNIT[1-2. Pytest Unit Tests & Business Logic]
```

### 📊 Матрица уровней тестирования

| Уровень | Фреймворк / Инструмент | Область покрытия | Скорость | Расположение тестов |
| :--- | :--- | :--- | :--- | :--- |
| **Unit (Бэкенд)** | `pytest`, `unittest.mock` | Бизнес-логика, манифест, чистые функции, fallback-алгоритмы | ~1-5 мс / тест | `tests/test_<module_id>.py` или `backend/modules/<module_id>/tests/` |
| **Storage & Persistence** | `pytest`, `tmp_path` | Создание, чтение, обновление, удаление записи в хранилище, миграции схем | ~10-20 мс / тест | `tests/test_<module_id>_storage.py` |
| **REST API Integration** | `fastapi.testclient.TestClient` | HTTP Эндпоинты модуля, валидация Pydantic-схем, RBAC (401/403) | ~50-100 мс / тест | `tests/test_<module_id>_api.py` |
| **Async & WebSockets** | `pytest-asyncio`, `AsyncMock` | Фоновые сервисы, отмена asyncio-тасок, `broadcaster`, lifecycle | ~20-50 мс / тест | `tests/test_<module_id>_async.py` |
| **Frontend Unit/Component** | `Vitest`, `Vue Test Utils` | Vue 3 SFC компоненты, виджеты, composables, маппинг данных | ~100-300 мс / тест | `frontend/src/modules/<module_id>/__tests__/` |
| **E2E (End-to-End)** | Node.js + MCP Chrome | Полный пользовательский сценарий в реальном браузере | ~3-10 сек / тест | `tests/mcp_chrome_*.js` |

---

## 📁 1. Структура и организация тестов модуля

> [!TIP]
> **Выбор стандарта размещения тестов**:
> - Для сторонних/пользовательских модулей рекомендуется использовать **Изолированный каталог модуля (`backend/modules/<module_id>/tests/`)**. Это позволяет распространять и подключать модуль как единый самодостаточный пакет вместе с его тестами.
> - Для встроенных системных плагинов ядра NMS-WebUI допускается размещение интеграционных тестов в корневой папочке `tests/`.

### 📌 Рекомендуемая топология файлов
Для сохранения чистоты кодовой базы тесты модуля могут располагаться в двух местах:

1. **Глобальный каталог `tests/` (рекомендуется для системных и интеграционных модулей)**:
   ```text
   nms-webui/
   ├── tests/
   │   ├── conftest.py                   # Глобальные фикстуры (app, mock_db, client)
   │   ├── test_tuya_module.py           # Юнит-тесты и жизненный цикл модуля Tuya
   │   ├── test_tuya_integration.py      # Интеграционные тесты Tuya API и Storage
   │   ├── test_widgets.py               # Тесты регистрации и работы виджетов
   │   └── test_module_i18n.py           # Тесты загрузки словарей локализации
   ```

2. **Изолированный каталог модуля `backend/modules/<module_id>/tests/`**:
   ```text
   backend/modules/sensor_monitor/
   ├── manifest.json
   ├── module.py
   ├── storage.py
   └── tests/
       ├── conftest.py                   # Локальные фикстуры модуля
       ├── test_unit.py                  # Внутренняя бизнес-логика
       └── test_api.py                   # Тесты REST API эндпоинтов
   ```

### 🧩 Стандартный шаблон `conftest.py` для тестов модуля

Для упрощения написания тестов в изолированном каталоге рекомендуется использовать следующий типовой файл `conftest.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from backend.core.plugin.context import ModuleContext
from backend.core.plugin.manifest import ModuleManifest

@pytest.fixture
def mock_module_dir(tmp_path: Path) -> Path:
    """Создает временный каталог для изоляции файлов модуля и хранилища."""
    mod_dir = tmp_path / "test_module"
    mod_dir.mkdir(parents=True, exist_ok=True)
    return mod_dir

@pytest.fixture
def mock_context(mock_module_dir: Path) -> ModuleContext:
    """Фикстура контекста модуля с изолированной файловой системой."""
    manifest_data = {
        "id": "sensor_monitor",
        "name": "Sensor Monitor Module",
        "version": "1.0.0",
        "permissions": ["sensor_monitor:read", "sensor_monitor:write"]
    }
    return ModuleContext(
        module_id="sensor_monitor",
        root=mock_module_dir,
        manifest=manifest_data,
    )

@pytest.fixture
def operator_token_headers() -> dict:
    """Заголовки авторизации с ролью оператора (только чтение)."""
    return {"Authorization": "Bearer mock_operator_jwt_token"}

@pytest.fixture
def admin_token_headers() -> dict:
    """Заголовки авторизации с ролью администратора (полный доступ)."""
    return {"Authorization": "Bearer mock_admin_jwt_token"}
```

---

## 🛠 2. Юнит-тестирование бизнес-логики и изоляция зависимостей

Юнит-тесты проверяют корректность логики модуля без реального взаимодействия с внешней сетью или базой данных. Внешние клиенты и интерфейсы изолируются с помощью `unittest.mock`.

### 🧪 Пример 1: Проверка манифеста и класса модуля (`ModuleContext`)

```python
import pytest
from pathlib import Path
from backend.core.plugin.context import ModuleContext
from backend.core.plugin.manifest import ModuleManifest
from backend.modules.tuya.module import TuyaModule

def test_tuya_module_lifecycle(tmp_path: Path):
    """Проверка инициализации и получения статуса модуля."""
    # 1. Создаем валидный манифест модуля
    manifest = ModuleManifest(id="tuya", name="Tuya Module", version="1.0.0")
    
    # 2. Инициализируем контекст модуля во временном каталоге tmp_path
    ctx = ModuleContext(
        module_id="tuya",
        root=tmp_path,
        manifest=manifest.to_api_dict(),
    )
    
    # 3. Создаем экземпляр модуля и запускаем init()
    module = TuyaModule(ctx)
    module.init()

    # 4. Проверяем начальное состояние и статус
    status = module.get_status()
    assert status["active"] is False
    assert status["total_devices"] == 0
    assert status["module_id"] == "tuya"
```

### 🧪 Пример 2: Мокирование внешних HTTP/Cloud клиентов и проверка Fallback-логики

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.modules.tuya.client import TuyaCloudClient, TuyaDeviceController

@pytest.mark.asyncio
async def test_tuya_device_controller_fallback():
    """Проверка отката на Cloud API, если локальное соединение недоступно (Auto Fallback)."""
    # Создаем мок Cloud-клиента
    mock_cloud = MagicMock(spec=TuyaCloudClient)
    mock_cloud.send_command = AsyncMock(return_value=True)

    controller = TuyaDeviceController(cloud_client=mock_cloud)

    # Запрос в режиме 'auto' без IP-адреса локального устройства -> должен вызывать Cloud API
    result = await controller.send_command(
        device_id="dev_auto_01",
        commands={"1": True},
        mode="auto",
        ip=None,
        local_key=None,
    )

    assert result is True
    # Убеждаемся, что вызов Cloud-клиента произошел ровно 1 раз
    mock_cloud.send_command.assert_called_once_with("dev_auto_01", {"1": True})
```

---

## 💾 3. Интеграционное тестирование Хранилища (Storage) и REST API

### 🧪 Пример 1: Изолированное тестирование Storage (`tmp_path`)

```python
from pathlib import Path
import pytest
from backend.modules.tuya.storage import TuyaStorage, TuyaDeviceSchema

def test_tuya_storage_crud_operations(tmp_path: Path):
    """Проверка полного цикла CRUD операций хранилища модуля."""
    storage = TuyaStorage(data_dir=tmp_path)
    assert len(storage.get_all()) == 0

    # 1. Create (Upsert)
    device = TuyaDeviceSchema(
        device_id="dev_100",
        name="Главный Коммутатор",
        ip="192.168.1.50",
        local_key="1234567890abcdef",
        mode="auto",
    )
    storage.upsert(device)

    # 2. Read
    loaded = storage.get("dev_100")
    assert loaded is not None
    assert loaded.name == "Главный Коммутатор"

    # 3. Update Status
    storage.update_status("dev_100", online=True, dps={"1": True})
    updated = storage.get("dev_100")
    assert updated.online is True
    assert updated.dps == {"1": True}

    # 4. Delete
    assert storage.delete("dev_100") is True
    assert storage.get("dev_100") is None
```

### 🧪 Пример 2: Интеграционное тестирование REST API через `FastAPI TestClient`

```python
import pytest
from fastapi.testclient import TestClient
from backend.core.app import create_app

@pytest.fixture
def api_client():
    """Фикстура для создания тестового HTTP-клиента FastAPI."""
    app = create_app()
    return TestClient(app)

def test_module_api_security_guard(api_client: TestClient):
    """Проверка защиты эндпоинтов модуля (401 Unauthorized без JWT)."""
    response = api_client.get("/api/v1/m/tuya/devices")
    assert response.status_code == 401

def test_module_api_authorized_access(api_client: TestClient, admin_token_headers: dict):
    """Проверка получения списка устройств с административным JWT токеном."""
    response = api_client.get("/api/v1/m/tuya/devices", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

### 🧪 Пример 3: Проверка прав доступа RBAC (`403 Forbidden`)

```python
def test_module_api_rbac_permissions(api_client: TestClient, operator_token_headers: dict):
    """Оператор без права 'tuya:write' должен получать 403 Forbidden при попытке удаления."""
    response = api_client.delete(
        "/api/v1/m/tuya/devices/dev_100",
        headers=operator_token_headers
    )
    assert response.status_code == 403
    payload = response.json()
    assert "Permission denied" in payload["detail"]
```

### 🧪 Пример 4: Проверка миграции схемы хранилища (Storage Schema Migration)

```python
import json
from pathlib import Path

def test_tuya_storage_schema_migration(tmp_path: Path):
    """Проверка загрузки устаревшей версии файла storage.json (v1) и автомиграции до v2."""
    storage_file = tmp_path / "tuya_devices.json"
    
    # Записываем старый формат данных (v1) без поля 'mode'
    v1_data = {
        "version": 1,
        "devices": {
            "dev_v1": {"device_id": "dev_v1", "name": "Старое Устройство", "ip": "10.0.0.1"}
        }
    }
    storage_file.write_text(json.dumps(v1_data), encoding="utf-8")

    # Инициализация хранилища должна успешно мигрировать данные и выставить значения по умолчанию
    storage = TuyaStorage(data_dir=tmp_path)
    device = storage.get("dev_v1")

    assert device is not None
    assert device.name == "Старое Устройство"
    assert device.mode == "auto"  # Поле по умолчанию из Pydantic схемы v2
```

---

## ⚡ 4. Тестирование асинхронных сервисов, WebSockets и фоновых задач

Модули NMS WebUI часто содержат фоновые задачи (Background Workers), опрашивающие оборудование или транслирующие метрики в реальном времени.

### 🧪 Пример 1: Тестирование генерации событий в EventBus (`broadcaster`)

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from backend.core.events import broadcaster

@pytest.mark.asyncio
async def test_module_background_worker_events():
    """Проверка генерации WebSocket-событий фоновой службой модуля."""
    # Мокируем функцию трансляции сообщений
    with patch.object(broadcaster, "broadcast", new_callable=AsyncMock) as mock_broadcast:
        # Симулируем событие об изменении состояния устройства
        event_payload = {
            "type": "device_status_changed",
            "module_id": "tuya",
            "device_id": "dev_100",
            "online": True
        }
        
        await broadcaster.broadcast(event_payload)
        
        # Проверяем, что брокер событий вызвал трансляцию
        mock_broadcast.assert_awaited_once_with(event_payload)
```

### 🧪 Пример 2: Проверка полного цикла жизни модуля (`init -> start -> stop -> shutdown`)

```python
@pytest.mark.asyncio
async def test_module_full_lifecycle_clean_shutdown(mock_context):
    """Проверка корректного освобождения ресурсов при останове модуля."""
    module = TuyaModule(mock_context)
    
    # 1. Инициализация и запуск
    module.init()
    await module.start()
    assert module.is_running is True

    # 2. Останов
    await module.stop()
    module.shutdown()
    
    # 3. Проверяем, что фоновые задачи завершены и ресурсы освобождены
    assert module.is_running is False
    assert len(module._active_tasks) == 0
```

### 🧪 Пример 3: Тестирование безопасного прерывания фонового цикла (`asyncio.CancelledError`)

```python
@pytest.mark.asyncio
async def test_background_poller_cancel_safety(mock_context):
    """Проверка того, что отмена фонового цикла не вызывает необработанных исключений."""
    module = TuyaModule(mock_context)
    
    # Запускаем бесконечный цикл опроса
    poll_task = asyncio.create_task(module._polling_loop())
    await asyncio.sleep(0.02)  # Даем итератору сделать шаг
    
    # Отменяем таску и проверяем мягкую обработку отмены
    poll_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await poll_task
```

---

## 🎨 5. Тестирование Виджетов, Локализации (i18n) и Логирования

### 🧩 1. Тестирование Виджетов (`test_widgets.py`)
```python
def test_widget_data_endpoint(api_client: TestClient, admin_token_headers: dict):
    """Проверка получения Pydantic-структуры данных для виджета модуля."""
    response = api_client.get(
        "/api/v1/m/tuya/widgets/tuya_overview/data",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert "widget_id" in payload
    assert "metrics" in payload
```

### 🌐 2. Тестирование Локализации (`test_module_i18n.py`)
```python
from backend.core.plugin.i18n import ModuleI18n

def test_module_translation_fallback(tmp_path: Path):
    """Проверка подстановки переводов и fallback на ключ/английский язык."""
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir()
    (locales_dir / "ru.json").write_text('{"status": "Статус", "hello": "Привет {name}"}', encoding="utf-8")

    i18n = ModuleI18n(module_id="sensor_monitor", locales_dir=locales_dir)
    
    # 1. Существующий ключ
    assert i18n.tr("ru", "status") == "Статус"
    # 2. Форматирование аргументов
    assert i18n.tr("ru", "hello", name="Алексей") == "Привет Алексей"
    # 3. Отсутствующий ключ -> возвращает сам ключ
    assert i18n.tr("ru", "unknown_key") == "unknown_key"
```

### 🪵 3. Тестирование Логирования (`caplog`)
```python
import logging

def test_module_logging_output(caplog, mock_context):
    """Проверка корректности формата и сообщений модуля в логах."""
    module = TuyaModule(mock_context)
    
    with caplog.at_level(logging.INFO):
        module.init()
        
    assert "Module tuya initialized" in caplog.text
```

---

## 🟢 6. Фронтенд автотесты компонентов (`Vitest` + Vue 3)

Фронтенд-часть модулей проверяется с помощью **Vitest**. Конфигурация находится в файле `frontend/package.json`.

### ⚙️ Запуск фронтенд тестов
```bash
cd frontend
npm run test          # Запуск Vitest в режиме прогона
npm run typecheck     # Проверка типов TypeScript (vue-tsc)
```

### 🧪 Пример: Тестирование Vue SFC Компонента Виджета (`TuyaWidget.spec.ts`)

```typescript
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import TuyaWidget from '../TuyaWidget.vue'

describe('TuyaWidget.vue', () => {
  it('отображает количество активных устройств и корректный статус', () => {
    const wrapper = mount(TuyaWidget, {
      props: {
        widgetData: {
          widget_id: 'tuya_overview',
          title: 'Устройства Tuya',
          status: 'online',
          metrics: [
            { label: 'Всего устройств', value: 12, unit: 'шт' }
          ]
        }
      }
    })

    expect(wrapper.text()).toContain('Устройства Tuya')
    expect(wrapper.text()).toContain('12 шт')
    expect(wrapper.find('.status-online').exists()).toBe(true)
  })

  it('генерирует событие action при клике на кнопку перезагрузки', async () => {
    const wrapper = mount(TuyaWidget, {
      props: { widgetData: { widget_id: 'tuya_overview' } }
    })

    const refreshBtn = wrapper.find('button.btn-refresh')
    await refreshBtn.trigger('click')

    expect(wrapper.emitted()).toHaveProperty('action')
    expect(wrapper.emitted('action')![0]).toEqual([{ action: 'refresh' }])
  })
})
```

---

## 🌐 7. Сквозное E2E тестирование (MCP Chrome E2E Suite)

Для проверки работы модуля в окружении реального браузера используется нативный тестовый комплекс NMS WebUI на базе Node.js и Chrome DevTools Protocol (`tests/mcp_chrome_*.js`).

### 📐 Структура E2E-сценария модуля (`tests/mcp_chrome_module_test.js`)

```javascript
import { chromium } from 'playwright'; // Или нативный скрипт MCP Chrome
import assert from 'assert';

(async () => {
  console.log('🚀 Запуск E2E теста модуля Tuya Integration...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    // 1. Авторизация в NMS WebUI
    await page.goto('http://localhost:5173/login');
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin_password');
    await page.click('#submit-btn');
    await page.waitForURL('http://localhost:5173/dashboard');

    // 2. Переход на страницу модуля
    await page.click('a[href="/m/tuya"]');
    await page.waitForSelector('.tuya-device-card');

    // 3. Проверка отображения списка устройств
    const deviceCards = await page.$$('.tuya-device-card');
    assert(deviceCards.length > 0, 'Список устройств Tuya не должен быть пустым');

    console.log('✅ E2E тест модуля Tuya успешно пройден!');
  } catch (error) {
    console.error('❌ Ошибка выполнения E2E теста:', error);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
```

---

## 🚀 8. Автоматизация прогона тестов в CI/CD (GitHub Actions / GitLab CI)

Для поддержания высокого уровня покрытия кода автотестами рекомендуется выполнять автоматическую проверку при каждом коммите и создании Pull Request.

### ⚙️ Пример конфигурации GitHub Actions (`.github/workflows/module-qa.yml`)

```yaml
name: Module QA Suite

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main, dev ]

jobs:
  backend-qa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
          
      - name: Run Backend Pytest Suite
        run: |
          pytest tests/ --cov=backend --cov-report=term-missing --cov-fail-under=80

  frontend-qa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Node.js 18
        uses: actions/setup-node@v3
        with:
          node-version: 18
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
          
      - name: Install Frontend Dependencies
        run: cd frontend && npm ci
        
      - name: Run Vue TypeScript Check
        run: cd frontend && npm run typecheck
        
      - name: Run Vitest Suite
        run: cd frontend && npm run test
```

---

## ✅ 9. Чек-лист готовности модуля (QA Readiness Checklist)

Перед слиянием кода модуля в продакшн-ветку разработчик обязан убедиться в выполнении следующих пунктов:

```mermaid
checklist
    [x] 1. Юнит-тесты бизнес-логики покрывают основные пути выполнения и граничные условия (Edge Cases).
    [x] 2. Интеграционные тесты проверяют создание, обновление и удаление данных в Storage (tmp_path) и миграции схем.
    [x] 3. Все REST API эндпоинты защищены проверкой авторизации (401) и проверкой ролевых прав RBAC (403).
    [x] 4. Асинхронные службы корректно завершают свою работу при вызове shutdown() и отмене asyncio-тасок.
    [x] 5. Фронтенд-компоненты проходят проверку типов vue-tsc --noEmit и Vitest тесты.
    [x] 6. Проверена локализация (ru/en) и отсутствие жестко зашитых текстовых строк (hardcoded text).
```

### 🚀 Запуск полного пакета автотестов проекта

```bash
# 1. Прогон всех бэкенд-тестов с выводом покрытия (используя виртуальное окружение .venv)
.venv/bin/pytest tests/ --cov=backend

# 2. Запуск проверки типов и юнит-тестов фронтенда
cd frontend && npm run typecheck && npm run test

# 3. Запуск E2E сюиты (при запущенном сервере)
node tests/mcp_e2e_full_suite.js
```
