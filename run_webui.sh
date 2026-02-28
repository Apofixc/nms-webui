#!/bin/bash
# Универсальный скрипт NMS-WebUI: запуск и установка.
# Использование:
#   Запуск:
#     ./run_webui.sh              — бэкенд + фронт (по умолчанию)
#     ./run_webui.sh all|backend|frontend|worker
#   Установка:
#     ./run_webui.sh install           — зависимости проекта (poetry, npm)
#     ./run_webui.sh install-all       — всё по порядку (libs + deps)

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

MODE="${1:-all}"
BACKEND_PORT="${NMS_PORT:-9000}"
FRONTEND_PORT="${NMS_FRONTEND_PORT:-5173}"
CELERY_BROKER="${NMS_CELERY_BROKER:-pyamqp://guest@localhost//}"

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

port_in_use() {
    local port="$1"
    ss -tlnp 2>/dev/null | grep -q ":${port} "
}

force_cleanup() {
    log "Проверка зависших процессов на портах $BACKEND_PORT и $FRONTEND_PORT..."
    
    # Очистка по портам
    for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
        PIDS=$(lsof -t -i :"$port" 2>/dev/null || true)
        if [ -n "$PIDS" ]; then
            warn "Освобождаю порт $port (PIDs: $PIDS)..."
            kill -9 $PIDS 2>/dev/null || true
        fi
    done

    # Дополнительная очистка uvicorn и vite
    pkill -9 -f "uvicorn" 2>/dev/null || true
    pkill -9 -f "vite" 2>/dev/null || true
    sleep 1
}

ensure_venv() {
    if [ ! -d ".venv" ]; then
        log "Создание виртуального окружения .venv..."
        python3 -m venv .venv
    fi
}

run_install() {
    log "=== Установка зависимостей проекта ==="
    
    ensure_venv
    
    log "--- Бэкенд ---"
    if command -v poetry &>/dev/null; then
        log "Использую системный poetry..."
        (cd backend && poetry install)
    else
        warn "Poetry не найден. Устанавливаю зависимости через pip в .venv..."
        # Устанавливаем основные зависимости из того, что мы знаем о проекте
        .venv/bin/pip install --upgrade pip
        .venv/bin/pip install fastapi "uvicorn[standard]" httpx pydantic pydantic-settings pyyaml celery
    fi
    
    log "--- Фронтенд (NPM) ---"
    if ! command -v npm &>/dev/null; then
        error "npm не найден. Пожалуйста, установите Node.js."
        exit 1
    fi
    (cd frontend && npm install)
    
    log "${GREEN}Установка завершена успешно.${NC}"
}

run_install_libs() {
    log "=== Установка системных библиотек ==="
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y python3-dev build-essential
    else
        warn "apt-get не найден. Убедитесь, что установлены python3-dev и средства сборки."
    fi
}

cleanup() {
    echo ""
    log "Остановка процессов..."
    [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
    [ -n "$WORKER_PID" ]   && kill "$WORKER_PID"   2>/dev/null || true
    exit 0
}

print_usage() {
    echo "Использование: $0 [режим]"
    echo ""
    echo "Запуск:"
    echo "  all       — бэкенд + фронт (по умолчанию)"
    echo "  backend   — только бэкенд"
    echo "  frontend  — только фронтенд"
    echo "  worker    — Celery worker"
    echo "  test-start — запуск тестовых инстансов Astra"
    echo "  test-stop  — остановка тестовых инстансов Astra"
    echo ""
    echo "Установка:"
    echo "  install      — зависимости проекта (poetry + npm)"
    echo "  install-libs — системные библиотеки (через sudo apt)"
    echo ""
    echo "Переменные: NMS_PORT, NMS_FRONTEND_PORT, NMS_CELERY_BROKER"
}

case "$MODE" in
    install)
        run_install
        exit 0
        ;;
    install-libs)
        run_install_libs
        exit 0
        ;;
    install-all)
        run_install_libs
        run_install
        exit 0
        ;;
    test-start)
        log "Запуск тестовых инстансов Astra..."
        (cd /opt/Cesbo-Astra-4.4.-monitor/lua && ./start_test.sh start)
        exit 0
        ;;
    test-stop)
        log "Остановка тестовых инстансов Astra..."
        (cd /opt/Cesbo-Astra-4.4.-monitor/lua && ./start_test.sh stop)
        exit 0
        ;;
    -h|--help)
        print_usage
        exit 0
        ;;
esac

trap cleanup SIGINT SIGTERM

case "$MODE" in
    all)
        force_cleanup
        ensure_venv
        log "Запуск полного стека NMS-WebUI..."
        
        # Backend
        if command -v poetry &>/dev/null; then
            (cd backend && poetry run uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT") &
        else
            PYTHONPATH=$PYTHONPATH:. .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
        fi
        BACKEND_PID=$!
        
        # Frontend
        (cd frontend && npm run dev -- --port "$FRONTEND_PORT" --host) &
        FRONTEND_PID=$!
        
        log "${GREEN}Сервисы запущены:${NC}"
        echo "  Backend:  http://127.0.0.1:$BACKEND_PORT"
        echo "  Frontend: http://127.0.0.1:$FRONTEND_PORT"
        echo "Остановка: Ctrl+C"
        wait
        ;;
    debug)
        force_cleanup
        ensure_venv
        log "Запуск полного стека NMS-WebUI..."
        
        # Backend
        if command -v poetry &>/dev/null; then
            (cd backend && poetry run uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT") &
        else
            PYTHONPATH=$PYTHONPATH:. .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
        fi
        BACKEND_PID=$!
        
        # Frontend
        (cd frontend && npm run dev -- --port "$FRONTEND_PORT" --host) &
        FRONTEND_PID=$!
        
        # Celery watcher removed temporarily since backend.main.celery_worker does not exist

        log "${GREEN}Сервисы запущены:${NC}"
        echo "  Backend:  http://127.0.0.1:$BACKEND_PORT"
        echo "  Frontend: http://127.0.0.1:$FRONTEND_PORT"
        echo "  Worker: запущен"
        echo "Остановка: Ctrl+C"
        wait
        ;;
    backend)
        force_cleanup
        ensure_venv
        log "Запуск бэкенда на порту $BACKEND_PORT..."
        if command -v poetry &>/dev/null; then
            (cd backend && poetry run uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT")
        else
            PYTHONPATH=$PYTHONPATH:. .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port "$BACKEND_PORT"
        fi
        ;;
        
    frontend)
        force_cleanup
        log "Запуск фронтенда на порту $FRONTEND_PORT..."
        (cd frontend && npm run dev -- --port "$FRONTEND_PORT" --host)
        ;;
        
    worker)
        ensure_venv
        log "Запуск Celery worker..."
        if command -v poetry &>/dev/null; then
            (cd backend && poetry run celery -A main.celery_worker worker --loglevel=info)
        else
            PYTHONPATH=$PYTHONPATH:. .venv/bin/celery -A backend.main.celery_worker worker --loglevel=info
        fi
        ;;
        
    *)
        print_usage
        exit 1
        ;;
esac
