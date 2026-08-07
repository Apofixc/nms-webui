# 🌐 11. Использование локализации (i18n API)

---

## 📌 1. Общая архитектура подсистемы i18n

Подсистема интернационализации и локализации (i18n) в **NMS-WebUI** построена на двухуровневом принципе:
- **Backend (Python / FastAPI)**: Утилиты извлечения языка из HTTP-запроса, контекстная функция переводов `tr()`, централизованный реестр `BACKEND_MESSAGES` и механизмы автоматической загрузки словарей модулей.
- **Frontend (Vue 3 / TypeScript)**: Реактивное управление текущим языком, полная поддержка плюрализации на базе стандартного `Intl.PluralRules`, цепочки поиска fallback-языков, динамическая загрузка локализаций модулей на лету без пересборки приложения и специализированные хелперы для предметных областей (роли RBAC, категории прав, имена модулей, форматирование дат и переводы ошибок API).

```mermaid
flowchart TD
    subgraph Frontend["Vue 3 Frontend (i18n.ts)"]
        UserLang["currentLang (ref: ru/en)"] --> Chain["getLanguageChain()"]
        Chain --> Plural["Intl.PluralRules (count)"]
        Plural --> Dict["translations dict"]
        Dict --> Output["t(key, params)"]
        API_Reg["registerModuleTranslations()"] --> Dict
    end

    subgraph Backend["FastAPI Backend (i18n.py)"]
        Req["HTTP Request"] --> GetLang["get_lang(request)"]
        GetLang --> TR["tr(request, key, en, **kwargs)"]
        TR --> CoreDict["BACKEND_MESSAGES"]
        ModScan["load_module_locales()"] --> CoreDict
        ManifestScan["manifest.i18n"] --> CoreDict
    end

    subgraph ModuleAPI["Module Locale Endpoint"]
        Endp["GET /api/v1/modules/{id}/locales/{lang}"]
    end

    Endp -->|"JSON Messages"| API_Reg
```

---

## 🐍 2. Бэкенд-локализация (`backend/core/i18n.py`)

### 2.1. Извлечение языка запроса (`get_lang`)

Язык текущего пользователя определяется функцией `get_lang(request)`:

```python
def get_lang(request: Optional[Request]) -> str:
    """Извлечь язык из параметров запроса или заголовков HTTP. По умолчанию 'en'."""
    if not request:
        return "en"
    query_lang = request.query_params.get("lang", "").lower()
    if query_lang in ("ru", "en"):
        return query_lang
    accept = request.headers.get("accept-language", "").lower()
    if "ru" in accept:
        return "ru"
    return "en"
```

**Приоритет определения языка:**
1. Явный query-параметр в URL (`?lang=ru` или `?lang=en`).
2. HTTP-заголовок `Accept-Language` (если содержит `ru`, выбирается `"ru"`).
3. По умолчанию возвращается `"en"`.

---

### 2.2. Функция перевода `tr()`

Функция `tr()` подготавливает локализованное сообщение для отправки клиенту:

```python
def tr(request: Optional[Request], key_or_ru: str, en: Optional[str] = None, **kwargs) -> str:
    """
    Вернуть локализованную строку по ключу или (ru, en) паре.
    Поддерживает подстановку параметров через kwargs.
    """
    lang = get_lang(request)
    if key_or_ru in BACKEND_MESSAGES:
        msg_dict = BACKEND_MESSAGES[key_or_ru]
        template = msg_dict.get(lang, msg_dict.get("en", key_or_ru))
        return template.format(**kwargs) if kwargs else template

    if en is not None:
        raw_text = key_or_ru if lang == "ru" else en
        return raw_text.format(**kwargs) if kwargs else raw_text

    return key_or_ru.format(**kwargs) if kwargs else key_or_ru
```

#### Способы вызова `tr()`:

1. **По централизованному ключу из словаря:**
   ```python
   from backend.core.i18n import tr

   # Использование зарегистрированного ключа с подстановкой параметров
   msg = tr(request, "sensorErrOverheat", name="Датчик-101", val=89.5)
   ```

2. **Через прямую пару строк (RU, EN):**
   ```python
   # Если ключ не зарегистрирован в словаре, указываются строки для RU и EN
   msg = tr(request, "Ошибка подключения к устройства {id}", "Device connection error {id}", id="DEV-42")
   ```

---

### 2.3. Регистрация и автоматическая загрузка словарей модулей

Словари локализации бэкенда собираются в едином объекте `BACKEND_MESSAGES` (`dict[str, dict[str, str]]`):
- Базовые словари ядра загружаются из `backend/core/locales/ru.py` и `backend/core/locales/en.py`.
- Модули могут регистрировать собственные локализации через `register_module_messages`:
  ```python
  from backend.core.i18n import register_module_messages

  register_module_messages({
      "tuya.device_not_found": {
          "ru": "Устройство Tuya '{id}' не найдено",
          "en": "Tuya device '{id}' was not found"
      }
  })
  ```
- При загрузке модуля через `loader.py` автоматически вызывается сканирование файлов `.json` из папки `locales/` модуля:
  ```python
  from backend.core.i18n import load_module_locales

  # Загрузит locales/ru.json, locales/en.json и т.д.
  load_module_locales(module_dir)
  ```

---

### 2.4. REST API локализации модулей

Бэкенд предоставляет специальный HTTP endpoint для отдачи локализаций конкретного модуля фронтенду:

- **Endpoint**: `GET /api/v1/modules/{module_id}/locales/{lang}`
- **Логика работы** (`backend/core/plugin/api.py`):
  1. Извлекает переводы из `manifest.i18n` для указанного языка.
  2. Объединяет их с данными из файла `modules/{module_id}/locales/{lang}.json` (при его наличии).
  3. Возвращает JSON-структуру:
     ```json
     {
       "module_id": "tuya",
       "lang": "ru",
       "messages": {
         "sensorTitle": "Мониторинг Датчиков",
         "sensorErrOverheat": "Внимание: Сенсор '{name}' перегрет ({val}°C)"
       }
     }
     ```

---

## 🎨 3. Фронтенд-локализация (`frontend/src/core/i18n.ts`)

### 3.1. Реактивное состояние языка и его переключение

В `frontend/src/core/i18n.ts` экпортируется реактивная переменная `currentLang` и функция управления языком `setLanguage`:

```typescript
export type Language = 'ru' | 'en'
export const DEFAULT_LANG: Language = 'en'

export const currentLang = ref<Language>(savedLang || defaultLang)

export function setLanguage(lang: Language) {
  currentLang.value = lang
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('nms_lang', lang)
  }
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lang
    window.dispatchEvent(new CustomEvent('nms-language-changed', { detail: { lang } }))
  }
}
```

- **Автодетекция**: при первом входе проверяется `navigator.language` (если начинается с `ru`, ставится `'ru'`, иначе `'en'`).
- **Сохранение**: выбранный язык сохраняется в `localStorage` под ключом `nms_lang`.
- **Синхронизация DOM и событий**: меняется атрибут `lang` элемента `<html>` и генерируется кастомное браузерное событие `nms-language-changed`.

---

### 3.2. Основная функция перевода `t()` и плюрализация

Функция `t(key, params)` осуществляет локализацию строк на фронтенде:

```typescript
export function t(key: string, params?: Record<string, string | number>): string
```

#### Ключевые возможности:

1. **Цепочка поиска языка (`getLanguageChain`)**:
   Если перевод отсутствует в активном языке (например, `ru`), система ищет ключ в `DEFAULT_LANG` (`en`), а затем в любых других доступных словарях. Если ключ не найден нигде, возвращается сам `key`.

2. **Поддержка вложенных ключей (Dot Notation)**:
   Поддерживаются ключи с точками, например: `t('dashboard.stats.total')`.

3. **Форматирование параметров**:
   Шаблон вида `"Привет, {name}"` автоматически заменяет `{name}` значением из объекта `params`.

4. **Плюрализация через `Intl.PluralRules`**:
   Если в `params` передано числовое поле `count`, функция формирует суффикс множественного числа с помощью стандартного браузерного `Intl.PluralRules(currentLang)`:
   - Сначала ищется ключ `${key}_${rule}` (например: `bulkActionSuccess_one`, `bulkActionSuccess_few`, `bulkActionSuccess_many`).
   - Если такой ключ найден, используется он; иначе происходит fallback на базовый `key`.

#### Пример плюрализации в словаре (`locales/ru.ts` и `locales/en.ts`):

```typescript
// ru.ts
bulkActionSuccess_one: 'Массовое действие выполнено ({count} пользователь)',
bulkActionSuccess_few: 'Массовое действие выполнено ({count} пользователя)',
bulkActionSuccess_many: 'Массовое действие выполнено ({count} пользователей)',

// en.ts
bulkActionSuccess_one: 'Bulk action applied ({count} user)',
bulkActionSuccess_other: 'Bulk action applied ({count} users)',
```

#### Использование в коде:
```typescript
t('bulkActionSuccess', { count: 1 }) // "Массовое действие выполнено (1 пользователь)"
t('bulkActionSuccess', { count: 3 }) // "Массовое действие выполнено (3 пользователя)"
t('bulkActionSuccess', { count: 5 }) // "Массовое действие выполнено (5 пользователей)"
```

---

### 3.3. Специализированные хелперы предметной области

Модуль `i18n.ts` предоставляет готовые вспомогательные функции для корректной локализации сущностей платформы:

| Функция | Описание |
| :--- | :--- |
| `getRoleTitle(roleName)` | Возвращает локализованное название роли RBAC (`superuser`, `admin`, `operator`, `viewer`). |
| `getRoleDescription(roleName, defaultDesc)` | Возвращает локализованное описание роли RBAC. |
| `translatePermissionCategory(category)` | Переводит системные и модульные категории прав доступа. |
| `translatePermissionName(permId, fallback)` | Переводит наименование конкретного права доступа. |
| `translatePermissionDesc(permId, fallback)` | Переводит описание права доступа. |
| `translateModuleName(nameOrId)` | Переводит имя модуля или ядра (`Core Engine` -> `Ядро системы`). |
| `translateApiError(err, fallbackKey)` | Маппит текст/код ошибки бэкенда на локализованное понятное сообщение. |
| `formatDateTime(date, options)` | Форматирует дату и время через `Intl` в текущей локали. |
| `formatTime(date, options)` | Форматирует время через `Intl` в текущей локали. |

---

### 3.4. Использование в Vue SFC компонентах через `useI18n()`

Во Vue-компонентах локализация подключается через composable `useI18n()`:

```vue
<script setup lang="ts">
import { useI18n } from '@/core/i18n'

const { 
  t, 
  lang, 
  setLanguage, 
  getRoleTitle, 
  translateApiError, 
  formatDateTime 
} = useI18n()

function handleLanguageChange(newLang: 'ru' | 'en') {
  setLanguage(newLang)
}
</script>

<template>
  <div class="user-profile">
    <h2>{{ t('userProfileTitle') }}</h2>
    <p>{{ t('currentLanguage') }}: {{ lang }}</p>

    <!-- Смена языка -->
    <div class="lang-switch">
      <button :class="{ active: lang === 'ru' }" @click="handleLanguageChange('ru')">RU</button>
      <button :class="{ active: lang === 'en' }" @click="handleLanguageChange('en')">EN</button>
    </div>

    <!-- Пример форматирования роли и даты -->
    <div class="info-badge">
      <span>{{ getRoleTitle('admin') }}</span>
      <time>{{ formatDateTime(new Date()) }}</time>
    </div>
  </div>
</template>
```

---

### 3.5. Динамическая загрузка локализаций модулей

При загрузке сторонних или динамических модулей их локализации считываются с бэкенда и инжектятся во фронтенд в режиме реального времени без перезагрузки страницы (`frontend/src/modules/registry.ts`):

```typescript
import { registerModuleTranslations } from '@/core/i18n'
import { http } from '@/core/api'

const loadedLocalesCache = new Set<string>()

export async function loadModuleLocales(moduleId: string, lang: string): Promise<void> {
    const cacheKey = `${moduleId}:${lang}`
    if (loadedLocalesCache.has(cacheKey)) return
    try {
        const { data } = await http.get(`/api/modules/${moduleId}/locales/${lang}`)
        if (data?.messages) {
            registerModuleTranslations({ [lang]: data.messages })
            loadedLocalesCache.add(cacheKey)
        }
    } catch {
        // ignore
    }
}
```

---

## 📦 4. Руководство для разработчика модуля

Разработчик модуля может объявить переводы двумя независимыми или дополняющими друг друга способами.

### Способ 1. В `manifest.yaml` (для небольших модулей)

Переводы описываются непосредственно в манифесте в секции `i18n`:

```yaml
id: "sensor_monitor"
name: "Sensor Monitor"
version: "1.0.0"

i18n:
  ru:
    sensorTitle: "Мониторинг Датчиков"
    sensorErrOverheat: "Внимание: Сенсор '{name}' перегрет ({val}°C)"
  en:
    sensorTitle: "Sensor Monitoring"
    sensorErrOverheat: "Warning: Sensor '{name}' overheated ({val}°C)"
```

---

### Способ 2. В папке `locales/` (для крупномасштабных модулей)

В корневой директории модуля создается папка `locales/` с JSON-файлами:

```text
my_module/
├── manifest.yaml
├── api.py
└── locales/
    ├── ru.json
    └── en.json
```

Содержимое `locales/ru.json`:
```json
{
  "sensor_monitor.title": "Панель датчиков",
  "sensor_monitor.status_ok": "Все датчики работают нормально",
  "sensor_monitor.status_warning": "Обнаружены отклонения"
}
```

Содержимое `locales/en.json`:
```json
{
  "sensor_monitor.title": "Sensor Panel",
  "sensor_monitor.status_ok": "All sensors operational",
  "sensor_monitor.status_warning": "Warnings detected"
}
```

---

### Рекомендации по именованию ключей (Best Practices)
1. **Используйте префиксы модулей**: Чтобы избежать коллизий с глобальными ключами, начинайте ключи с идентификатора модуля: `my_module.button_save`.
2. **Симметрия ключей**: Все ключи, существующие в `ru.json`, должны обязательно присутствовать в `en.json`.
3. **Параметризация вместо конкатенации**: Запрещено собирать строки из частей руками (`t('hello') + ' ' + name`). Используйте шаблоны: `t('helloUser', { name })`.

---

## 🧪 5. Тестирование подсистемы локализации

### 5.1. Фронтенд-тесты (Vitest)

Проверка симметрии ключей и корректности работы плюрализации в `frontend/src/core/__tests__/i18n.test.ts`:

```typescript
import { describe, test, expect } from 'vitest'
import { translations, t, setLanguage, registerModuleTranslations } from '../i18n'

describe('i18n subsystem', () => {
  test('симметрия ключей между RU и EN', () => {
    const ruKeys = Object.keys(translations.ru)
    const enKeys = Object.keys(translations.en)

    const missingInEn = ruKeys.filter((k) => !(k in translations.en))
    const missingInRu = enKeys.filter((k) => !(k in translations.ru))

    expect(missingInEn).toEqual([])
    expect(missingInRu).toEqual([])
  })

  test('плюрализация для русского языка', () => {
    setLanguage('ru')
    expect(t('bulkActionSuccess', { count: 1 })).toBe('Массовое действие выполнено (1 пользователь)')
    expect(t('bulkActionSuccess', { count: 2 })).toBe('Массовое действие выполнено (3 пользователя)')
    expect(t('bulkActionSuccess', { count: 5 })).toBe('Массовое действие выполнено (5 пользователей)')
  })

  test('динамическая регистрация переводов модуля', () => {
    registerModuleTranslations({
      ru: { custom_key: 'Тест' },
      en: { custom_key: 'Test' }
    })
    setLanguage('ru')
    expect(t('custom_key')).toBe('Тест')
  })
})
```

---

### 5.2. Бэкенд-тесты (Pytest)

Проверка автоматической загрузки словарей в `tests/test_module_i18n.py`:

```python
import json
from pathlib import Path
import tempfile
from backend.core.i18n import register_module_messages, load_module_locales, BACKEND_MESSAGES

def test_register_module_messages():
    register_module_messages({
        "custom_module.test_key": {"ru": "Тест", "en": "Test"}
    })
    assert "custom_module.test_key" in BACKEND_MESSAGES
    assert BACKEND_MESSAGES["custom_module.test_key"]["ru"] == "Тест"

def test_load_module_locales():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        locales_dir = tmp_path / "locales"
        locales_dir.mkdir()

        (locales_dir / "ru.json").write_text(json.dumps({"loaded_key": "Загружено"}), encoding="utf-8")
        (locales_dir / "en.json").write_text(json.dumps({"loaded_key": "Loaded"}), encoding="utf-8")

        load_module_locales(tmp_path)

        assert BACKEND_MESSAGES["loaded_key"]["ru"] == "Загружено"
        assert BACKEND_MESSAGES["loaded_key"]["en"] == "Loaded"
```
