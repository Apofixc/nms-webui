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
    pkill -9 -f "test_signal_generator.py" 2>/dev/null || true
    pkill -9 -f "mediamtx" 2>/dev/null || true
    pkill -9 -f "http.server" 2>/dev/null || true
    
    # Останавливаем тестовую Астру
    if [ -d "/opt/Cesbo-Astra-4.4.-monitor/lua" ]; then
        (cd /opt/Cesbo-Astra-4.4.-monitor/lua && ./start_test.sh stop >/dev/null 2>&1 || true)
    fi
    
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
        .venv/bin/pip install fastapi "uvicorn[standard]" httpx pydantic pydantic-settings pyyaml celery structlog
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
    if command -v poetry &>/dev/null; then
        (cd backend && poetry run uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT") &
    else
        PYTHONPATH=$PYTHONPATH:. .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
    fi
    BACKEND_PID=$!
}

start_frontend() {
    log "Запуск Frontend (порт $FRONTEND_PORT)..."
    (cd frontend && npm run dev -- --port "$FRONTEND_PORT" --host) &
    FRONTEND_PID=$!
}

start_signals() {
    log "Запуск генератора сигналов (все протоколы)..."
    PYTHONPATH=$PYTHONPATH:. .venv/bin/python3 backend/modules/stream/scripts/test_signal_generator.py all >/dev/null 2>&1 &
    SIGNAL_PID=$!
}

start_astra_test() {
    if [ -d "/opt/Cesbo-Astra-4.4.-monitor/lua" ]; then
        log "Запуск тестовых инстансов Astra..."
        (cd /opt/Cesbo-Astra-4.4.-monitor/lua && ./start_test.sh start >/dev/null 2>&1 || true)
    fi
}

# --- Основная логика ---

print_usage() {
    echo -e "${GREEN}Использование:${NC} $0 <команда>"
    echo ""
    echo "Основные команды:"
    echo "  install      — Полная установка (системные пакеты + python + node)"
    echo "  dev          — Обычный запуск для разработки (Backend + Frontend)"
    echo "  test         — Полный запуск для тестов (Dev + Сигналы + Тестовая Astra)"
    echo "  stop         — Остановить все процессы и очистить порты"
    echo ""
    echo "Дополнительные команды:"
    echo "  backend      — Только бэкенд"
    echo "  frontend     — Только фронтенд"
    echo "  worker       — Celery worker"
    echo "  signal [pr]  — Запустить генератор сигналов отдельно (по умолчанию all)"
}

trap "force_cleanup; exit 0" SIGINT SIGTERM

MODE="${1:-help}"

case "$MODE" in
    install)
        run_install
        ;;
    
    dev)
        force_cleanup
        ensure_venv
        start_backend
        start_frontend
        log "${GREEN}NMS-WebUI (Dev) запущен. Нажмите Ctrl+C для остановки.${NC}"
        wait
        ;;

    test)
        force_cleanup
        ensure_venv
        start_astra_test
        start_signals
        start_backend
        start_frontend
        log "${GREEN}NMS-WebUI (Full Test Mode) запущен.${NC}"
        echo " - Сигналы генерируются"
        echo " - Тестовые инстансы Astra активны"
        wait
        ;;

    stop)
        force_cleanup
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

    worker)
        ensure_venv
        log "Запуск Celery worker..."
        (cd backend && .venv/bin/celery -A main.celery_worker worker --loglevel=info)
        ;;

    signal)
        PROTO="${2:-all}"
        ensure_venv
        log "Запуск генератора сигналов ($PROTO)..."
        PYTHONPATH=$PYTHONPATH:. .venv/bin/python3 backend/modules/stream/scripts/test_signal_generator.py "$PROTO"
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
