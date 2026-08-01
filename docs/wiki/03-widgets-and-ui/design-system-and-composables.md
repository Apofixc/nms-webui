# Дизайн-система, Стилизация и Composables

Справочник по визуальным стандартам Material 3, Tailwind CSS классам, цветовой палитре и вспомогательным Vue Composables в NMS WebUI.

---

## 🎨 Дизайн-система (Material 3 Tokens)

Интерфейс NMS WebUI спроектирован по спецификации **Material 3 Expressive Design** в тёмном исполнении с neon-акцентами.

### Ключевая цветовая палитра:

- **Surface Container (Фон блоков)**:
  - Base surface: `bg-surface` (`#0f172a`)
  - Low container: `bg-surface-container-low` (`#1e293b`)
  - High container: `bg-surface-container-high` (`#334155`)
- **Text & Content (Текст)**:
  - On-surface: `text-on-surface` (`#f8fafc`) — основной текст.
  - On-surface-variant: `text-on-surface-variant` (`#94a3b8`) — второстепенный текст и подписи.
- **Accents (Акцентные цвета)**:
  - Primary: `bg-primary` / `text-primary` (`#22d3ee` / cyan-400).
  - Primary Bright: `text-primary-bright` (`#06b6d4`).
  - Outline / Borders: `border-outline-variant` (`#334155`).

### Световые эффекты (Glow Effects):
Для создания современного премиум-вида используется утилита `shadow-glow`:
```html
<div class="bg-surface-container-low border border-outline-variant/60 rounded-xl p-4 shadow-glow">
  Контентый блок со свечением
</div>
```

---

## 🧩 Иконки (Material Symbols)

В проекте используются векторы **Google Material Symbols Outlined**.

Пример использования во Vue-компонентах:
```html
<span class="material-symbols-outlined text-primary text-xl">settings</span>
```

Рекомендуемые иконки для модулей:
- `cpu`, `devices`, `router`, `memory` — железо и серверы.
- `lock`, `key`, `shield` — безопасность и права.
- `bar_chart`, `show_chart`, `query_stats` — метрики и виджеты.

---

## 🛠️ Вспомогательные Vue Composables

В директории `frontend/src/composables/` и `src/core/` доступны следующие переиспользуемые Composables:

### 1. `useAuthStore` (`@/core/stores/auth`)
Управление профилем пользователя и проверкой разрешений:
```typescript
import { useAuthStore } from '@/core/stores/auth'

const authStore = useAuthStore()

// Проверка наличия конкретного права
if (authStore.hasPermission('module.tuya.view')) {
  // Показать раздел
}

// Данные текущего пользователя
console.log(authStore.user?.username, authStore.user?.role_name)
```

### 2. `useI18n` (`@/core/i18n`)
Доступ к функции перевода строки по ключу:
```typescript
import { useI18n } from '@/core/i18n'

const { t, locale } = useI18n()
const translatedTitle = t('tuyaTitle')
```

---

## 📏 Стандарты адаптивности и сеток

Все компоненты должны быть адаптивными:
- **Мобильный вид**: `flex flex-col gap-4 w-full`.
- **Планшет и Десктоп**: `md:grid md:grid-cols-2 lg:grid-cols-3 gap-6`.
- **Карточки**: Обязательные скругления `rounded-xl` или `rounded-2xl` с прозрачной рамкой `border border-outline-variant/40`.
