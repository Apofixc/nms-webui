# 🌿 3. Разработка субмодулей и иерархия плагинов (`BaseSubmodule`)

---

## 📌 Концепция и назначение субмодулей

Субмодули в **NMS WebUI** позволяют разбивать крупные модули на дочерние независимые компоненты. Это полезно для создания семейств драйверов оборудования (например, родительский модуль `network_drivers` и дочерние субмодули `cisco`, `juniper`, `mikrotik`).

### Местоположение субмодулей в проекте:
```
backend/modules/<parent_id>/
├── manifest.yaml                      # Манифест родительского модуля
├── submodules/                        # Директория субмодулей
│   ├── <submodule_id_1>/
│   │   └── manifest.yaml              # Манифест дочернего субмодуля
│   └── <submodule_id_2>/
│       └── manifest.yaml
```

---

## 📜 Оформление манифеста субмодуля

В манифесте субмодуля поле `parent` явно указывает системный ID родительского модуля:

```yaml
id: cisco                                # Внутренний ID субмодуля
parent: network_drivers                  # ID родительского модуля
name: ciscoTitle                         # Название или ключ i18n
version: 1.0.0
type: driver

entrypoints:
  factory: "backend.modules.network_drivers.submodules.cisco:create_submodule"
  router: "backend.modules.network_drivers.submodules.cisco.api:router"
```

При сканировании Загрузчик (`loader.py`):
1. Формирует полный составной идентификатор вида: `network_drivers.cisco`.
2. Автоматически добавляет родительский модуль `network_drivers` в список обязательных зависимостей `deps`.

---

## 🐍 Класс `BaseSubmodule`

Субмодули бэкенда наследуются от абстрактного класса `BaseSubmodule` (`backend/modules/base.py`):

```python
from abc import ABC
from backend.modules.base import BaseSubmodule
from backend.core.plugin.context import ModuleContext

class CiscoSubmodule(BaseSubmodule):
    def __init__(self, context: ModuleContext):
        super().__init__(context)

    @property
    def parent_id(self) -> str | None:
        """Возвращает ID родительского модуля ('network_drivers')."""
        return self.parent_module_id

    def init(self) -> None:
        self.context.logger.info("Initializing Cisco submodule for parent %s", self.parent_id)

    def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def get_status(self) -> dict:
        return {"status": "ok", "parent": self.parent_id}

def create_submodule(context: ModuleContext) -> BaseSubmodule:
    return CiscoSubmodule(context)
```

---

## 🛠 Доступ к родительскому модулю из субмодуля

Субмодуль может взаимодействовать с экземпляром родительского модуля через контекст `ModuleContext`:

```python
parent_instance = self.context.get_module_instance(self.context.parent_module_id)
if parent_instance:
    parent_instance.register_driver(self.context.module_id, self)
```
