# 📡 17. Шина событий EventBus (Pub/Sub Events)

---

Платформа **NMS WebUI** предоставляет внутрипроцессную шину событий **EventBus** для обмена сообщениями в реальном времени между ядром системы и подключаемыми модулями по шаблону издатель-подписчик (Pub/Sub).

Шина событий обеспечивает слабую связанность компонентов, автоподстановку идентификатора модуля, поддержку wildcard-масок, автоматическую очистку подписок при выгрузке модулей, изоляцию ошибок подписчиков и мост для трансляции событий веб-клиентам через WebSockets.

---

## 🧭 1. Архитектурная модель

```mermaid
flowchart TD
    Core[Ядро NMS / Auth / Loader] -- "publish('core.*')" --> Bus[EventBus (backend/core/bus.py)]
    ModA[Модуль Tuya (ctx.events)] -- "publish('devices.down')" --> Bus
    ModB[Модуль Astra (ctx.events)] -- "publish('channels.alert')" --> Bus

    Bus -- "match_topic()" --> Sub1[Подписчик 1 (Core Handler)]
    Bus -- "match_topic()" --> Sub2[Подписчик 2 (Module Handler)]
    Bus -- "broadcast" --> WSBridge[EventBusWsBridge (backend/core/events.py)]

    WSBridge --> WSClient[WebSocket Клиенты / Браузеры]
```

### 📊 Основные характеристики EventBus

| Характеристика | Описание |
| :--- | :--- |
| **Формат топиков** | Иерархическая строка из сегментов: `<module_id>.<домен>.<событие>` |
| **Зарезервированные топики** | Префикс `core.*` зарезервирован исключительно за ядром системы |
| **Автоподстановка префикса** | Вызов `ctx.events.publish("devices.down")` автоматизирует короткую форму в `tuya.devices.down` |
| **Wildcard-маски** | Символ `*` на любом сегменте (`core.*.enabled`, `*.devices.down`, `tuya.*`, `*`) |
| **Изоляция ошибок** | Исключения в обработчиках подписчиков логируются и не прерывают рассылку остальным |
| **Жизненный цикл** | При деактивации/выгрузке модуля подписки автоматически отписываются |
| **WS Мост** | Все события шины транслируются клиентам WebSockets через `EventBusWsBridge` |

---

## 🔒 2. Формат наименования топиков и защита `core.*`

Наименование топика состоит из разделенных точками сегментов:
- **События модулей**: `<module_id>.<домен>.<событие>` (например, `tuya.devices.down`, `astra.channels.status_changed`).
- **События ядра**: `core.<домен>.<событие>` (например, `core.modules.enabled`, `core.users.login`).

### 🛡️ Резервирование первого сегмента `core`
Публикация в топики с префиксом `core.` разрешена **только** коду ядра (при вызове `event_bus.publish(..., is_core=True)`). 

Если модуль пытается опубликовать событие в топик `core.*` через `ctx.events.publish()` или напрямую с `is_core=False`, генерируется исключение `PermissionDeniedError`.

---

## 💻 3. Использование шины в модулях (`ctx.events`)

Модули взаимодействуют с шиной событий через объект `ctx.events`, предоставляемый в контексте `ModuleContext`.

### 📤 3.1. Публикация событий (`publish`)

```python
# Публикация с использованием короткой формы (автоматически преобразуется в 'tuya.devices.down')
ctx.events.publish("devices.down", {
    "device_id": "dev-101",
    "reason": "connection_timeout"
})

# Публикация с явным указанием полного топика модуля
ctx.events.publish("tuya.devices.down", {"device_id": "dev-101"})
```

### 📥 3.2. Подписка на события (`subscribe`)

Обработчики могут быть как синхронными (`def`), так и асинхронными (`async def`).

```python
# Синхронный обработчик
def on_device_down(topic: str, payload: dict):
    ctx.logger.warning("Устройство недоступно (топик: %s): %s", topic, payload)

# Асинхронный обработчик
async def on_core_module_event(payload: dict):
    ctx.logger.info("Изменено состояние модуля: %s", payload)

# Регистрация подписок
ctx.events.subscribe("tuya.devices.down", on_device_down)
ctx.events.subscribe("core.modules.*", on_core_module_event)
```

### ❌ 3.3. Отписка от событий (`unsubscribe`)

```python
# Отписка конкретной функции-обработчика
ctx.events.unsubscribe("tuya.devices.down", on_device_down)

# Отписка по маске или по обработчику
ctx.events.unsubscribe(on_device_down)
```

---

## 🎯 4. Wildcard-маски сопоставления тем (`match_topic`)

Шина поддерживает гибкое сопоставление подписок с топиками публикаций с использованием символа `*`:

```python
# 1. Замена одного сегмента на любой позиции:
bus.subscribe("core.*.enabled", handler)   # Совпадает с 'core.modules.enabled'
bus.subscribe("*.devices.down", handler)   # Совпадает с 'tuya.devices.down', 'zigbee.devices.down'

# 2. Маска для всех подтопиков префикса:
bus.subscribe("tuya.devices.*", handler)   # Совпадает с 'tuya.devices.down', 'tuya.devices.up'

# 3. Глобальная подписка:
bus.subscribe("*", handler)                 # Совпадает с любым опубликованным топиком
```

---

## ⚙️ 5. Изоляция ошибок и жизненный цикл

### 🛡️ Изоляция ошибок подписчиков
Если один из обработчиков при получении события выбрасывает исключение, `EventBus` перехватывает ошибку, записывает в лог стек вызовов через `logger.exception` и продолжит рассылку события остальным подписчикам. Упавший обработчик не может нарушить работу шины.

### 🧹 Автоматическая очистка подписок (`cleanup`)
При деактивации модуля (`set_module_enabled(module_id, False)`) или при остановке/выгрузке модуля (`unload_single_module_async(module_id)`), система автоматически вызывает метод `ctx.events.cleanup()`, который отписывает все зарегистрированные данным модулем обработчики.

---

## 🌉 6. Интеграция с WebSocket клиентов (`EventBusWsBridge`)

Все события, публикуемые в `EventBus`, автоматически транслируются в WebSocket сокеты подключенных веб-клиентов через объект `EventBusWsBridge` в `backend/core/events.py`.

Клиент веб-интерфейса получает сообщение следующего формата:

```json
{
  "type": "bus_event",
  "topic": "tuya.devices.down",
  "payload": {
    "device_id": "dev-101",
    "reason": "connection_timeout"
  }
}
```

---

## 📢 7. Встроенные события ядра (`core.*`)

Ядро системы автоматически генерирует следующие стандартные события:

| Топик | Описание | Полезная нагрузка (`payload`) |
| :--- | :--- | :--- |
| `core.modules.loaded` | Модуль успешно загружен и инициализирован | `{"module_id": "tuya"}` |
| `core.modules.enabled` | Модуль переведен в состояние Включен | `{"module_id": "tuya"}` |
| `core.modules.disabled` | Модуль переведен в состояние Отключен | `{"module_id": "tuya"}` |
| `core.users.login` | Пользователь успешно авторизовался в системе | `{"user_id": "usr-root", "username": "admin"}` |
