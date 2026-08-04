# 🏗 Виджеты и Дизайн-система (Widget System & Design System)

---

## 🖼 Система виджетов (Widget System)

Интерфейс NMS WebUI строится на основе модульных дашбордов и слотов.

### Ключевые компоненты системы виджетов:
1. **Реестр виджетов** (`widgets.ts`): Карта всех зарегистрированных UI-виджетов в системе.
2. **Рендерер виджетов** (`WidgetRenderer.vue`): Универсальный компонент, отвечающий за динамическое монтирование Vue-компонента по его имени/ID в соответствующий слот.

```svg
<svg viewBox="0 0 700 240" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad-card" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="grad-slot" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
    <linearGradient id="grad-widget" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3b82f6"/>
      <stop offset="100%" stop-color="#2563eb"/>
    </linearGradient>
  </defs>

  <rect x="10" y="10" width="680" height="220" rx="16" fill="url(#grad-card)" stroke="#475569" stroke-width="2" filter="drop-shadow(0 4px 14px rgba(0,0,0,0.4))"/>
  <text x="350" y="38" fill="#94a3b8" font-size="14" font-weight="bold" text-anchor="middle" font-family="sans-serif">Dashboard Grid Page</text>

  <g transform="translate(35, 55)">
    <rect width="300" height="150" rx="12" fill="url(#grad-slot)" stroke="#3b82f6" stroke-width="1.5" stroke-dasharray="4,4"/>
    <text x="150" y="28" fill="#60a5fa" font-size="12" font-weight="bold" text-anchor="middle" font-family="sans-serif">WidgetSlot ("top")</text>
    
    <rect x="25" y="45" width="250" height="85" rx="10" fill="url(#grad-widget)"/>
    <text x="150" y="72" fill="#ffffff" font-size="12" font-weight="bold" text-anchor="middle" font-family="sans-serif">WidgetRenderer</text>
    <text x="150" y="95" fill="#dbeafe" font-size="11" text-anchor="middle" font-family="sans-serif">► StatusCard Component</text>
  </g>

  <g transform="translate(365, 55)">
    <rect width="300" height="150" rx="12" fill="url(#grad-slot)" stroke="#8b5cf6" stroke-width="1.5" stroke-dasharray="4,4"/>
    <text x="150" y="28" fill="#c084fc" font-size="12" font-weight="bold" text-anchor="middle" font-family="sans-serif">WidgetSlot ("sidebar")</text>
    
    <rect x="25" y="45" width="250" height="85" rx="10" fill="#7c3aed"/>
    <text x="150" y="72" fill="#ffffff" font-size="12" font-weight="bold" text-anchor="middle" font-family="sans-serif">WidgetRenderer</text>
    <text x="150" y="95" fill="#ede9fe" font-size="11" text-anchor="middle" font-family="sans-serif">► StreamPlayer Component</text>
  </g>
</svg>
```

---

## 🎨 Дизайн-система и Темы

NMS WebUI использует строгую, современную дизайн-систему на основе **CSS-переменных (Tokens)**.

### Переменные оформления (Theme Tokens):
При написании компонентов рекомендуется использовать системные переменные вместо хардкода цветов:

```css
.custom-card {
  background-color: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
}
```
