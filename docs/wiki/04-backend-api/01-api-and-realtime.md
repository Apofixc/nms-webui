# ⚙️ Backend REST API и Реальный Время (WebSockets & SSE)

---

## 📡 Полный справочник REST API Эндпоинтов

Бэкенд NMS WebUI предоставляет специфицированный REST API на базе FastAPI. Вся документация по схеме OpenAPI генерируется автоматически и доступна при запущенном бэкенде по адресам:
- **Swagger UI**: `http://localhost:9000/docs`
- **ReDoc UI**: `http://localhost:9000/redoc`

### 1. Группа Аутентификации и Сессий (`/api/auth`)

| Метод | Эндпоинт | Требуемые права | Описание |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Публичный | Первичная авторизация по логину и паролю. Возвращает JWT токен либо билетик MFA (`mfa_ticket`). |
| `POST` | `/api/auth/mfa/verify` | Публичный | Второй шаг авторизации. Валидация 6-значного TOTP кода по `mfa_ticket`. |
| `POST` | `/api/auth/mfa/setup` | Bearer Token | Генерация нового Base32 секрета и SVG QR-кода для настройки 2FA. |
| `POST` | `/api/auth/mfa/enable` | Bearer Token | Подтверждение 6-значного кода и включение 2FA в аккаунте. |
| `POST` | `/api/auth/mfa/disable` | Bearer Token | Отключение 2FA (если не включена принудительная политика `force_mfa`). |
| `POST` | `/api/auth/logout` | Bearer Token | Выход из системы и отзыв текущего токена `jti`. |
| `POST` | `/api/auth/terminate-sessions` | Bearer Token | Завершение всех активных сессий текущего пользователя на всех устройствах. |
| `GET` | `/api/auth/me` | Bearer Token | Получение данных о текущем авторизованном пользователе и его списка прав. |

### 2. Группа Пользователей и Ролей RBAC (`/api/users`, `/api/roles`)

| Метод | Эндпоинт | Требуемые права | Описание |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/users` | `users.view` | Список пользователей с пагинацией, поиском и реальным онлайн-статусом. |
| `POST` | `/api/users` | `users.manage` | Создание нового пользователя с валидацией сложности пароля. |
| `PUT` | `/api/users/me` | Bearer Token | Обновление собственного профиля (ФИО, email, аватар). |
| `PUT` | `/api/users/me/password` | Bearer Token | Смена собственного пароля с подтверждением старого. |
| `PUT` | `/api/users/{user_id}` | `users.manage` | Редактирование роли, статуса активности или данных пользователя. |
| `DELETE` | `/api/users/{user_id}` | `users.manage` | Удаление пользователя (запрещено удаление системного `root`). |
| `GET` | `/api/roles` | `roles.view` | Получить список ролей и назначенную матрицу разрешений. |
| `POST` | `/api/roles` | `roles.manage` | Создание новой пользовательской роли. |
| `PUT` | `/api/roles/{role_id}` | `roles.manage` | Изменение прав доступа роли (автоматически сбрасывает кэш прав). |
| `GET` | `/api/permissions` | `roles.view` | Получить список всех доступных в системе прав доступа. |

### 3. Группа Системного Администрирования (`/api/system`)

| Метод | Эндпоинт | Требуемые права | Описание |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/system/health` | Публичный | Статус здоровья системы: проверка SQLite, свободного места на диске и статуса модулей. |
| `GET` | `/api/system/backup` | `system.admin` | Скачать бинарный файл резервной копии базы данных `nms.db`. |
| `POST` | `/api/system/restore` | `system.admin` | Восстановить базу данных из загруженного файла `.db` с проверкой целостности. |
| `GET` | `/api/system/logs` | `system.admin` | Список всех зарегистрированных провайдеров логов. |
| `GET` | `/api/system/logs/{log_name}` | `system.admin` | Чтение последних N строк лога с фильтрацией по уровням (`ERROR`, `WARN`). |
| `GET` | `/api/system/logs/{log_name}/download` | `system.admin` | Скачать полный файл лога. |
| `GET` | `/api/system/logs/remote-sources/list` | `system.admin` | Список подключенных удаленных серверов логов. |
| `POST` | `/api/system/logs/remote-sources` | `system.admin` | Добавить новый удаленный сервер логов (HTTP API). |
| `DELETE` | `/api/system/logs/remote-sources/{id}` | `system.admin` | Удалить удаленный сервер логов. |
| `GET` | `/api/system/sessions` | `system.admin` | Список всех активных сессий пользователей с IP и User-Agent. |
| `POST` | `/api/system/sessions/terminate-all` | `system.admin` | Принудительный сброс токенов всех пользователей. |
| `GET` | `/api/system/security-settings` | `system.admin` | Чтение системных настроек безопасности (IP вайтлист, TTL, lockout). |
| `PUT` | `/api/system/security-settings` | `system.admin` | Сохранение настроек безопасности. |

### 4. Группа Динамических Модулей и Вики (`/api/modules`, `/api/system/docs`)

| Метод | Эндпоинт | Требуемые права | Описание |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/modules` | `modules.view` | Список всех сканированных плагинов и их манифестов. |
| `POST` | `/api/modules/scan` | `modules.manage` | Принудительное повторное сканирование директории `backend/modules/`. |
| `PUT` | `/api/modules/{module_id}/toggle` | `modules.manage` | Включение или выключение модуля в режиме реального времени. |
| `GET` | `/api/modules/{module_id}/views` | `modules.view` | Получить список доступных UI-представлений модуля. |
| `GET` | `/api/modules/{module_id}/locales/{lang}` | Публичный | Динамическая загрузка переходов локализации модуля для языка `{lang}`. |
| `GET` | `/api/system/docs/wiki/tree` | Bearer Token | Получить структуру категорий и файлов Вики-документации. |
| `GET` | `/api/system/docs/wiki/article` | Bearer Token | Получить текст статьи вики по её относительному пути. |

---

## ⚠️ Формат Ошибок и Статусы Ответа

Все ошибки системы возвращаются в строго едином JSON-формате через доменные подклассы `NMSError`:

```json
{
  "error": {
    "code": "ACCOUNT_LOCKED_DURATION",
    "message": "Аккаунт временно заблокирован на 30 минут из-за превышения числа неверных вводов пароля.",
    "details": {
      "lockout_duration": 30
    }
  }
}
```

### Основные HTTP Статусы:
- **`200 OK`**: Успешное выполнение запроса.
- **`400 Bad Request`**: Ошибка валидации входящих данных или параметров.
- **`401 Unauthorized`**: Отсутствует, истек или аннулирован Bearer токен.
- **`403 Forbidden`**: Недостаточно прав у роли пользователя или доступ запрещен по IP.
- **`404 Not Found`**: Запрашиваемый ресурс, модуль или лог-провайдер не найден.
- **`429 Too Many Requests`**: Временная блокировка из-за превышения попыток входа.
- **`500 Internal Server Error`**: Внутренняя ошибка сервера.

---

## 🔄 Событийная модель реального времени (WebSockets)

Для информирования клиентов об изменениях используется протокол **WebSockets** (эндпоинт `/api/events/ws`). Ранее применявшийся SSE (Server-Sent Events) устарел и переведен на WebSockets.

### WebSockets `/api/events/ws`
Используется компонент `ConnectionManager`. Поддерживает двусторонний обмен и пинг-понги для поддержания активности соединения:

- **Отправка от клиента**: `"ping"`
- **Ответ бэкенда**: `{"type": "pong"}`
- **Рассылка от бэкенда (Broadcast)**:
```json
{
  "type": "device_status_changed",
  "timestamp": "2026-08-04T23:15:00Z",
  "data": {
    "device_id": "tuya-plug-01",
    "status": "online",
    "power_watt": 42.5
  }
}
```

### 3. WebSockets стриминг логов `/api/system/logs/{log_name}/stream`
Эндпоинт позволяет получать только новые добавляемые строки лога в режиме реального времени раз в секунду:

```json
{
  "id": "backend.log",
  "name": "Основной лог бэкенда",
  "content": [
    "2026-08-04 23:15:01 [INFO] nms.app: User root logged in successfully"
  ],
  "matched_lines": 1,
  "total_lines": 1420
}
```
