# Быстрый старт (Quick Start)

## Системные требования и зависимости [icon:fact_check]

Система NMS WebUI запускается с помощью универсального скрипта управления `run_webui.sh`. Требования к серверу зависят от выбранного режима работы.

### Требования к ресурсам

| Режим работы | Команда запуска | Процессор (CPU) | Оперативная память (RAM) | Свободный диск |
| :--- | :--- | :--- | :--- | :--- |
| **Разработка (Dev)** | `./run_webui.sh dev` | 2 ядра (x86_64 / ARM64) | 2–4 ГБ RAM | 5 ГБ |
| **Тестовый режим (Test)** | `./run_webui.sh test` | 2–4 ядра | 4 ГБ RAM | 5 ГБ |
| **Продакшн (Production)** | `./run_webui.sh backend` | 2+ ядра | 2+ ГБ RAM | 10 ГБ SSD |

### Поддерживаемые операционные системы
- **Linux**: Ubuntu 20.04/22.04/24.04, Debian 11/12, RHEL / Rocky Linux 8/9, Alpine Linux.
- **macOS**: macOS 12+ (Apple Silicon или Intel).
- **Windows**: Windows 10/11 в среде **WSL2** (Ubuntu/Debian).

### Системные зависимости
- **Python**: `>= 3.10` (`python3-venv`, `python3-dev`).
- **Node.js**: `>= 18.x` (`npm`).
- **Системные утилиты**: `bash`, `git`, `lsof`, `procps`, `build-essential`.

---

## Установка и локальный запуск одной командой [icon:download]

Вся установка и запуск управляющих процессов NMS WebUI производятся через скрипт `run_webui.sh`.

### 1. Клонирование репозитория
```bash
git clone https://github.com/your-org/nms-webui.git
cd nms-webui
```

### 2. Автоматическая полная установка (`install`)
```bash
./run_webui.sh install
```

**Что делает команда `install`**:
1. Проверяет наличие `apt-get` и при необходимости устанавливает `python3-dev`, `build-essential`, `lsof`, `procps`.
2. Создает виртуальное окружение `.venv` и устанавливает зависимости Python (`FastAPI`, `Uvicorn`, `httpx`, `Pydantic v2`, `Structlog`, `PyYAML`).
3. Устанавливает зависимости фронтенда в папке `frontend/` через `npm install`.

### 3. Запуск веб-интерфейса (`dev`)
```bash
./run_webui.sh dev
```

- **Backend API**: запущен на порту `9000` (`http://localhost:9000`, Swagger UI по адресу `http://localhost:9000/docs`).
- **Frontend WebUI**: запущен на порту `5173` (`http://localhost:5173`).

### 4. Тестовый запуск (`test`)
```bash
./run_webui.sh test
```

### 5. Раздельные команды
```bash
./run_webui.sh backend     # Запустить только Backend API
./run_webui.sh frontend    # Запустить только Frontend UI
./run_webui.sh worker      # Запустить Celery worker
./run_webui.sh reset-root  # Сбросить пароль суперадминистратора
```

### 6. Остановка процессов (`stop`)
```bash
./run_webui.sh stop
```

---

## Конфигурация первого запуска [icon:tune]

### Переменные окружения (`.env`)
Создайте файл `.env` в корне проекта (на основе `.env.example` при необходимости):

```ini
# Уровень логирования
NMS_LOG_LEVEL=INFO

# Порты сервисов
NMS_PORT=9000
NMS_FRONTEND_PORT=5173
```

### Запуск без авторизации (для локальной отладки)
Для отладочных целей можно временно отключить форму входа:
```bash
./run_webui.sh dev --no-auth
```
