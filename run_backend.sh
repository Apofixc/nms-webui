#!/bin/bash
cd "$(dirname "$0")"
export PATH="/usr/bin:/usr/local/bin:${PATH:-}"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
exec .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port "${NMS_PORT:-9000}"
