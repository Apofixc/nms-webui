#!/bin/bash
# RQ-воркер для тяжёлых задач (обновление превью каналов и др.).
# Требуется Redis и NMS_REDIS_URL в бэкенде. Запускайте воркер отдельно от основного процесса.
# Пример: NMS_REDIS_URL=redis://localhost:6379/0 ./run_worker.sh

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export PATH="/usr/bin:/usr/local/bin:${PATH:-}"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$ROOT"

REDIS_URL="${NMS_REDIS_URL:-redis://localhost:6379/0}"
echo "Запуск RQ worker (очередь nms), Redis: $REDIS_URL"
exec .venv/bin/python -m rq worker --url "$REDIS_URL" nms
