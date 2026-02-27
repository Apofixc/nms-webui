#!/bin/bash
# Универсальный скрипт NMS WebUI: запуск и установка.
# Использование:
#   Запуск:
#     ./run_webui.sh              — бэкенд + фронт (по умолчанию)
#     ./run_webui.sh all|backend|frontend|worker
#   Установка:
#     ./run_webui.sh install           — зависимости проекта (venv, pip, npm)
#     ./run_webui.sh install-libs      — системные библиотеки (sudo)
#     ./run_webui.sh install-stream-tools — FFmpeg, VLC, GStreamer, TSDuck (sudo)
#     ./run_webui.sh install-all       — всё выше по порядку
# Остановка запущенных процессов: Ctrl+C.

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

MODE="${1:-all}"
BACKEND_PORT="${NMS_PORT:-9000}"
FRONTEND_PORT="${NMS_FRONTEND_PORT:-5175}"
REDIS_URL="${NMS_REDIS_URL:-redis://localhost:6379/0}"

port_in_use() {
  local port="$1"
  if command -v ss &>/dev/null; then
    ss -tlnp 2>/dev/null | grep -q ":${port} "
  else
    python3 -c "
import socket, sys
port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.5)
try:
    r = s.connect_ex(('127.0.0.1', port))
    sys.exit(0 if r == 0 else 1)
finally:
    s.close()
" "$port" 2>/dev/null
  fi
}

ensure_backend_deps() {
  if [ ! -d .venv ]; then
    echo "Создание виртуального окружения Python..."
    python3 -m venv .venv
  fi
  .venv/bin/python -m pip install -q -r requirements.txt
}

ensure_frontend_deps() {
  if [ ! -d frontend/node_modules ]; then
    echo "Установка зависимостей фронтенда (npm install)..."
    (cd frontend && npm install)
  fi
}

# --- Установка системных библиотек (для Python venv и сборки пакетов) ---
run_install_libs() {
  echo "=== Установка системных библиотек ==="
  if ! command -v apt-get &>/dev/null; then
    echo "Обнаружена не Debian/Ubuntu-система. Установите вручную: Python 3.8+, python3-venv, Node.js и npm." >&2
    return 0
  fi
  echo "Требуется sudo для apt-get."
  sudo apt-get update -qq
  sudo apt-get install -y \
    python3 \
    python3-venv \
    python3-dev \
    build-essential
  if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
    echo "Установка Node.js и npm..."
    if apt-cache show nodejs &>/dev/null; then
      sudo apt-get install -y nodejs npm
    else
      echo "Node.js не в репозиториях. Установите вручную: https://nodejs.org/" >&2
    fi
  fi
  echo "Системные библиотеки установлены."
}

# --- Установка зависимостей проекта (venv + pip + npm) ---
run_install() {
  echo "=== Установка зависимостей проекта ==="
  if ! command -v python3 &>/dev/null; then
    echo "Ошибка: python3 не найден. Выполните: $0 install-libs" >&2
    exit 1
  fi
  echo "Python: $(python3 --version)"
  if [ ! -d .venv ]; then
    echo "Создание виртуального окружения .venv..."
    if ! python3 -m venv .venv 2>/dev/null; then
      echo "Ошибка: не удалось создать venv. Выполните: $0 install-libs" >&2
      exit 1
    fi
  fi
  echo "Установка пакетов из requirements.txt..."
  .venv/bin/pip install -r requirements.txt
  echo "Python-зависимости установлены."

  echo ""
  echo "--- Фронтенд (Node/npm) ---"
  if ! command -v npm &>/dev/null; then
    echo "Предупреждение: npm не найден. Выполните: $0 install-libs (или установите Node.js)." >&2
    echo "Бэкенд можно запускать отдельно: $0 backend" >&2
  else
    echo "Установка зависимостей в frontend/..."
    (cd frontend && npm install)
    echo "Фронтенд-зависимости установлены."
  fi
  echo ""
  echo "Готово. Запуск: $0"
}

# --- Установка инструментов потоков (FFmpeg, VLC, GStreamer, TSDuck) ---
run_install_stream_tools() {
  SCRIPT="$ROOT/scripts/install-stream-tools.sh"
  if [ ! -f "$SCRIPT" ]; then
    echo "Скрипт не найден: $SCRIPT" >&2
    exit 1
  fi
  echo "=== Установка инструментов потоков (FFmpeg, VLC, GStreamer, TSDuck) ==="
  echo "Требуется sudo."
  sudo bash "$SCRIPT"
}

# --- Полная установка: libs → deps → stream-tools ---
run_install_all() {
  run_install_libs
  echo ""
  run_install
  echo ""
  run_install_stream_tools
  echo ""
  echo "=== Установка завершена ==="
  echo "Запуск: $0"
}

# --- Вывод справки ---
print_usage() {
  echo "Использование: $0 [режим]" >&2
  echo "" >&2
  echo "Запуск:" >&2
  echo "  all       — бэкенд + фронт (по умолчанию)" >&2
  echo "  backend   — только бэкенд" >&2
  echo "  frontend  — только фронтенд" >&2
  echo "  worker    — только RQ-воркер (нужен Redis)" >&2
  echo "" >&2
  echo "Установка:" >&2
  echo "  install             — зависимости проекта (venv, pip, npm)" >&2
  echo "  install-libs        — системные библиотеки (sudo)" >&2
  echo "  install-stream-tools — FFmpeg, VLC, GStreamer, TSDuck (sudo)" >&2
  echo "  install-all         — install-libs + install + install-stream-tools" >&2
  echo "" >&2
  echo "Переменные: NMS_PORT, NMS_FRONTEND_PORT, NMS_REDIS_URL" >&2
}

cleanup() {
  echo ""
  echo "Остановка..."
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  [ -n "$WORKER_PID" ]   && kill "$WORKER_PID"  2>/dev/null || true
  [ -n "$TELEGRAF_PID" ] && kill "$TELEGRAF_PID" 2>/dev/null || true
  exit 0
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
  install-stream-tools)
    run_install_stream_tools
    exit 0
    ;;
  install-all)
    run_install_all
    exit 0
    ;;
  -h|--help)
    print_usage
    exit 0
    ;;
esac

# Режимы запуска: нужен trap для корректного завершения
trap cleanup SIGINT SIGTERM
export PATH="/usr/bin:/usr/local/bin:${PATH:-}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$ROOT"

case "$MODE" in
  all)
    if port_in_use "$BACKEND_PORT"; then
      echo "Ошибка: порт $BACKEND_PORT (бэкенд) уже занят. Остановите другой процесс или задайте NMS_PORT." >&2
      exit 1
    fi
    if port_in_use "$FRONTEND_PORT"; then
      echo "Ошибка: порт $FRONTEND_PORT (фронт) уже занят. Остановите другой процесс или задайте NMS_FRONTEND_PORT." >&2
      exit 1
    fi
    ensure_backend_deps
    ensure_frontend_deps
    .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port "$BACKEND_PORT" &
    BACKEND_PID=$!
    (cd frontend && npm run dev -- --port "$FRONTEND_PORT") &
    FRONTEND_PID=$!
    echo "NMS WebUI запущен (бэкенд + фронт)."
    echo "  Backend:  http://127.0.0.1:$BACKEND_PORT"
    echo "  Frontend: http://127.0.0.1:$FRONTEND_PORT"
    echo "Остановка: Ctrl+C"
    ;;
  backend)
    if port_in_use "$BACKEND_PORT"; then
      echo "Ошибка: порт $BACKEND_PORT уже занят. Задайте NMS_PORT или остановите другой процесс." >&2
      exit 1
    fi
    ensure_backend_deps
    .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port "$BACKEND_PORT"
    ;;
  frontend)
    if port_in_use "$FRONTEND_PORT"; then
      echo "Ошибка: порт $FRONTEND_PORT уже занят. Задайте NMS_FRONTEND_PORT или остановите другой процесс." >&2
      exit 1
    fi
    ensure_frontend_deps
    (cd frontend && npm run dev -- --port "$FRONTEND_PORT")
    ;;
  worker)
    ensure_backend_deps
    echo "Запуск RQ worker (очередь nms), Redis: $REDIS_URL"
    exec .venv/bin/python -m rq worker --url "$REDIS_URL" nms
    ;;
  *)
    print_usage
    exit 1
    ;;
esac

[ "$MODE" = "all" ] && wait
