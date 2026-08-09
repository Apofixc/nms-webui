#!/bin/bash
# Универсальный скрипт NMS-WebUI: запуск и установка.

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Настройки портов (можно переопределить через ENV)
BACKEND_PORT="${NMS_PORT:-9000}"
FRONTEND_PORT="${NMS_FRONTEND_PORT:-5173}"

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Вспомогательные функции ---

force_cleanup() {
    log "Очистка запущенных процессов..."
    
    # Убиваем по портам
    for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
        PIDS=$(lsof -t -i :"$port" 2>/dev/null || true)
        [ -n "$PIDS" ] && kill -9 $PIDS 2>/dev/null || true
    done

    # Убиваем по именам процессов
    pkill -9 -f "uvicorn" 2>/dev/null || true
    pkill -9 -f "vite" 2>/dev/null || true
    pkill -9 -f "http.server" 2>/dev/null || true
    
    log "Система очищена."
}

ensure_venv() {
    if [ ! -d ".venv" ]; then
        log "Создание виртуального окружения .venv..."
        python3 -m venv .venv
    fi
}

# --- Команды установки ---

run_install() {
    log "=== Полная установка NMS-WebUI ==="
    
    # 1. Системные зависимости
    if command -v apt-get &>/dev/null; then
        log "Установка системных библиотек..."
        sudo apt-get update -qq && sudo apt-get install -y python3-dev build-essential lsof procps
    fi

    # 2. Бэкенд
    ensure_venv
    log "Установка зависимостей Python..."
    if command -v poetry &>/dev/null; then
        (cd backend && poetry install)
    else
        .venv/bin/pip install --upgrade pip
        .venv/bin/pip install fastapi "uvicorn[standard]" httpx pydantic pydantic-settings pyyaml structlog openpyxl
    fi

    # 3. Фронтенд
    log "Установка зависимостей Node.js..."
    if command -v npm &>/dev/null; then
        (cd frontend && npm install)
    else
        error "npm не найден! Установите Node.js."
        exit 1
    fi

    log "${GREEN}Установка завершена успешно.${NC}"
}

# --- Команды запуска ---

start_backend() {
    log "Запуск Backend (порт $BACKEND_PORT)..."
    NO_AUTH_ARG=""
    [ "$NMS_DISABLE_AUTH" = "1" ] && NO_AUTH_ARG="--no-auth"
    if command -v poetry &>/dev/null; then
        (cd backend && poetry run uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" --ws-max-size 65536 --ws-per-message-deflate true $NO_AUTH_ARG) &
    else
        PYTHONPATH=$PYTHONPATH:. .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --ws-max-size 65536 --ws-per-message-deflate true $NO_AUTH_ARG --reload &
    fi

    BACKEND_PID=$!
}

start_frontend() {
    log "Запуск Frontend (порт $FRONTEND_PORT)..."
    (cd frontend && npm run dev -- --port "$FRONTEND_PORT" --host) &
    FRONTEND_PID=$!
}

print_usage() {
    echo -e "${GREEN}Использование:${NC} $0 <команда> [опции]"
    echo ""
    echo "Основные команды:"
    echo "  install      — Полная установка (системные пакеты + python + node)"
    echo "  dev          — Обычный запуск для разработки (Backend + Frontend)"
    echo "  stop         — Остановить все процессы и очистить порты"
    echo ""
    echo "Дополнительные команды:"
    echo "  backend      — Только бэкенд"
    echo "  frontend     — Только фронтенд"
    echo "  reset-root   — Сброс пароля пользователя root к 'admin'"
    echo ""
    echo "Опции авторизации:"
    echo "  --no-auth, --disable-auth — Отключить форму входа (авто-доступ под Superuser)"
}

trap "force_cleanup; exit 0" SIGINT SIGTERM

MODE=""
HAS_NO_AUTH=0
for arg in "$@"; do
    case "$arg" in
        --no-auth|--disable-auth|no-auth)
            export NMS_DISABLE_AUTH=1
            HAS_NO_AUTH=1
            ;;
        *)
            if [ -z "$MODE" ]; then
                MODE="$arg"
            fi
            ;;
    esac
done

if [ "$HAS_NO_AUTH" -eq 1 ]; then
    warn "Авторизация отключена через параметр запуска. Доступ к веб-интерфейсу предоставляется автоматически под Superuser."
fi

MODE="${MODE:-help}"

case "$MODE" in
    install)
        run_install
        ;;
    
    dev)
        force_cleanup
        ensure_venv
        start_backend
        start_frontend
        log "${GREEN}NMS-WebUI запущен. Нажмите Ctrl+C для остановки.${NC}"
        wait
        ;;

    stop)
        force_cleanup
        ;;

    reset-root)
        ensure_venv
        PYTHONPATH=. .venv/bin/python3 -m backend.scripts.reset_root
        ;;

    backend)
        force_cleanup
        ensure_venv
        start_backend
        wait
        ;;

    frontend)
        force_cleanup
        start_frontend
        wait
        ;;


    help|-h|--help)
        print_usage
        ;;

    *)
        error "Неизвестная команда: $MODE"
        print_usage
        exit 1
        ;;
esac
