# 📜 18. Контракты модулей (contract.py) и правила импортов

---

## 📌 1. Архитектурный принцип

Главный критерий архитектурного взаимодействия в платформе **NMS WebUI**:
> **«Всё, что требует `module_id` — через `ctx`; остальное — прямой импорт из публичного API ядра (`backend.core.public`)»**.

Этот принцип решает ключевые проблемы модульных платформ:
1. Убирает жесткое зацепление (tight coupling) модулей за внутренние реализации ядра.
2. Гарантирует изоляцию настроек, фоновых задач, логов и аудита между модулями.
3. Предотвращает неконтролируемые межмодульные зависимости и каскадные сбои.

---

## 🏛️ 2. Публичный интерфейс ядра (`backend.core.public`)

Модулям разрешён прямой импорт только из публичного фасада `backend.core.public` (или через `backend.core`).

### Разрешённые классы и декораторы

```python
from backend.core.public import (
    # Контракты и контекст модулей
    BaseModule,
    BaseSubmodule,
    ModuleStatusResponse,
    ModuleContext,
    
    # Авторизация и доступ
    CurrentUser,
    require_permission,
    require_module_permission,
    
    # Стандартные ошибки NMS
    NMSError,
    NMSModuleNotFoundError,
    ModuleDisabledError,
    AuthenticationError,
    PermissionDeniedError,
    NotFoundError,
    ValidationError,
    ModuleValidationError,
)
```

> [!CAUTION]
> **Прямой импорт** из внутренних модулей ядра (`backend.core.events`, `backend.core.database`, `backend.core.audit`, `backend.core.log_providers`, `backend.core.scheduler`) в коде модулей **строго запрещён**.
> Используйте соответствующий API `ModuleContext` (`ctx.broadcast`, `ctx.get_db()`, `ctx.audit()`, `ctx.settings`, `ctx.register_log_provider()`).

---

## 🤝 3. Соглашение о контрактах модулей (`contract.py`)

Если модуль `mod_A` предоставляет интерфейсы, DTO или базовые структуры данных для других модулей, он объявляет файл `contract.py` в корне своей директории (`backend/modules/mod_A/contract.py`).

### Содержимое `contract.py`
Файл `contract.py` содержит **исключительно чисто декларативный код**:
- Pydantic-модели и DTO.
- Enums и константы.
- TypedDict, TypeAliases.
- Абстрактные интерфейсы и протоколы (`typing.Protocol`, `abc.ABC`).

> [!WARNING]
> В `contract.py` **запрещено** помещать тяжелую бизнес-логику, выполнение SQL-запросов, инициализацию сетевых подключений или глобальные побочные эффекты (side effects).

#### Пример `contract.py`:
```python
# backend/modules/network_topology/contract.py
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field

class NodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"

class NetworkNodeDTO(BaseModel):
    node_id: str
    ip_address: str
    status: NodeStatus
    labels: dict[str, str] = Field(default_factory=dict)
```

---

## 🔗 4. Правила межмодульного импорта

Модуль `mod_A` может импортировать чужие модули только при соблюдении следующих 2 правил:

1. **Разрешён только `contract.py`**: Модуль `mod_A` может импортировать **только** `backend.modules.mod_B.contract`. Импорт `backend.modules.mod_B.services`, `views`, `models` и т.д. строго запрещен.
2. **Явное объявление в манифесте**: Модуль `mod_B` должен быть предварительно объявлен в манифесте `mod_A` (`manifest.json` или `manifest.yaml`) в разделах `dependencies` (`deps`) или `optional_dependencies` (`optional_deps`).

#### Пример импорта:
```python
# backend/modules/sensor_monitor/services.py
# Разрешено, если "network_topology" есть в deps или optional_deps манифеста
from backend.modules.network_topology.contract import NetworkNodeDTO, NodeStatus
```

---

## 🔍 5. Линт-контроль импортов в CI (`check_module_imports.py`)

Для автоматической проверки соблодения правил в CI/CD платформы разработан AST-линтер `scripts/check_module_imports.py`.

### Запуск проверки:
```bash
python3 scripts/check_module_imports.py
```

### Алгоритм работы линтера:
1. Сканирует все `.py` файлы в директории `backend/modules/`.
2. Анализирует AST деревева импортов (`import` и `from ... import`).
3. При обнаружении прямого импорта незащищённых модулей `backend.core.*` генерирует ошибку.
4. При обнаружении межмодульного импорта без объявления зависимости в манифесте или при попытке импортировать файлы помимо `contract.py` генерирует ошибку.
