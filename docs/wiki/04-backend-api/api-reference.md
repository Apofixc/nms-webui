# Справочник REST API NMS WebUI

Полный справочник основных конечных точек (endpoints) системного API NMS WebUI.

---

## 🔑 Авторизация и управления доступом (`/api/auth`)

### `POST /api/auth/login`
Авторизация пользователя и генерация JWT доступа.
- **Тело запроса**: `application/x-www-form-urlencoded` или JSON (`username`, `password`).
- **Ответ**: `{ "access_token": "<token>", "token_type": "bearer" }`

### `GET /api/auth/me`
Получение профиля текущего авторизованного пользователя и списка его прав.
- **Заголовки**: `Authorization: Bearer <token>`
- **Ответ**: `{ "id": 1, "username": "admin", "permissions": ["*"] }`

---

## ⚙️ Системное администрирование (`/api/system`)

### `GET /api/system/health`
Детализированный статус здоровья системы (БД, диск, статус загруженных модулей).
- **Ответ**:
```json
{
  "status": "ok",
  "database": { "status": "ok" },
  "disk": { "free_gb": 45.2, "percent_used": 12.4 },
  "modules": [{ "id": "tuya", "status": "active" }]
}
```

### `GET /api/system/backup`
Скачать резервную копию базы данных SQLite (`nms.db`).
- **Права**: `system.admin`
- **Тип ответа**: `application/x-sqlite3`

### `POST /api/system/restore`
Восстановление состояния базы данных из загружаемого `.db` файла.
- **Права**: `system.admin`

### `GET /api/system/logs`
Получение списка зарегистрированных провайдеров логов.

### `GET /api/system/logs/{log_name}`
Чтение текстового лога с фильтрацией по уровням (`INFO`, `ERROR`) и поисковой строке.

---

## 📚 Вики и Документация (`/api/system/docs`)

### `GET /api/system/docs/wiki/tree`
Получение иерархического дерева категорий и статей документации.

### `GET /api/system/docs/wiki/article?path={path}`
Получение текста статьи Markdown по её относительному пути.

---

## 🧩 Управление модулями (`/api/modules`)

### `GET /api/modules`
Получение списка всех обнаруженных модулей и их статусов.

### `POST /api/modules/scan`
Принудительное повторное сканирование директории `modules/`.

### `POST /api/modules/install`
Загрузка и разархивация нового zip-пакета модуля.
