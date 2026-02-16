#!/bin/bash
# Запуск Telegraf с конфигом проекта. Сначала запустите бэкенд (./run_backend.sh).
cd "$(dirname "$0")"
exec telegraf --config telegraf.conf
