#!/bin/bash
# Запуск NMS WebUI: бэкенд + фронт (и опционально Telegraf) одним скриптом.
# Остановка: Ctrl+C (завершаются все процессы).

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

BACKEND_PORT="${NMS_PORT:-9000}"
FRONTEND_PORT="${NMS_FRONTEND_PORT:-5173}"

# Проверка: порты не должны быть заняты (чтобы не запускать второй экземпляр)
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

if port_in_use "$BACKEND_PORT"; then
  echo "Ошибка: порт $BACKEND_PORT (бэкенд) уже занят. Остановите другой процесс или задайте NMS_PORT." >&2
  exit 1
fi
if port_in_use "$FRONTEND_PORT"; then
  echo "Ошибка: порт $FRONTEND_PORT (фронт) уже занят. Остановите другой процесс или задайте NMS_FRONTEND_PORT." >&2
  exit 1
fi

cleanup() {
  echo "Остановка..."
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  [ -n "$TELEGRAF_PID" ] && kill "$TELEGRAF_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# 1) Бэкенд
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
export PYTHONPATH="${PYTHONPATH}:$ROOT"
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port "$BACKEND_PORT" &
BACKEND_PID=$!

# 2) Фронт
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi
(cd frontend && npm run dev -- --port "$FRONTEND_PORT") &
FRONTEND_PID=$!

# 3) Telegraf (опционально: раскомментировать при необходимости)
# if command -v telegraf >/dev/null 2>&1; then
#   telegraf --config "$ROOT/telegraf.conf" &
#   TELEGRAF_PID=$!
# fi

echo "NMS WebUI запущен."
echo "  Backend:  http://127.0.0.1:$BACKEND_PORT"
echo "  Frontend: http://127.0.0.1:$FRONTEND_PORT"
echo "Остановка: Ctrl+C"
wait
