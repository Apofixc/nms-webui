#!/bin/bash

# Скрипт для генерации тестовых потоков (UDP Multicast/Unicast, HTTP, HLS) на базе одного источника
# Для работы требуется установленный ffmpeg
# Использование: ./generate_streams.sh [исходный_url]
# По умолчанию используется: http://31.130.202.110/httpts/tv3by/avchigh.ts

SOURCE_URL=${1:-"http://31.130.202.110/httpts/tv3by/avchigh.ts"}
OUTPUT_DIR="/tmp/test_streams"

# Настройки выходных потоков
UDP_MULTICAST_URL="udp://239.0.0.1:1234?pkt_size=1316"
UDP_UNICAST_URL="udp://127.0.0.1:1235?pkt_size=1316"
HTTP_TS_PORT=8080
HTTP_TS_URL="http://127.0.0.1:${HTTP_TS_PORT}/stream.ts"
HLS_DIR="${OUTPUT_DIR}/hls"
HLS_URL="http://127.0.0.1:${HTTP_TS_PORT}/hls/stream.m3u8"

echo "====================================================="
echo " Запуск генератора тестовых потоков NMS-WebUI"
echo " Источник: $SOURCE_URL"
echo "====================================================="

# Проверка ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ Ошибка: ffmpeg не установлен. Пожалуйста, установите его (apt install ffmpeg)."
    exit 1
fi

# Подготовка директорий
mkdir -p "$HLS_DIR"
rm -f "$HLS_DIR"/*

echo "✅ Создана директория для HLS: $HLS_DIR"

# Функция для остановки всех запущенных процессов
cleanup() {
    echo ""
    echo "🛑 Остановка всех потоков..."
    kill $(jobs -p) 2>/dev/null
    rm -rf "$OUTPUT_DIR"
    echo "✅ Все процессы завершены."
    exit 0
}

# Перехватываем Ctrl+C
trap cleanup SIGINT SIGTERM

echo ""
echo "📡 Запускаем трансляции (каждая в фоновом режиме):"

# 1. UDP Multicast
echo "  -> UDP Multicast: $UDP_MULTICAST_URL"
ffmpeg -hide_banner -loglevel error -re -i "$SOURCE_URL" -c copy -f mpegts "$UDP_MULTICAST_URL" &

# 2. UDP Unicast
echo "  -> UDP Unicast:   $UDP_UNICAST_URL"
ffmpeg -hide_banner -loglevel error -re -i "$SOURCE_URL" -c copy -f mpegts "$UDP_UNICAST_URL" &

# 3. HTTP TS (через встроенный HTTP сервер ffmpeg)
# ffmpeg может отдать только одному клиенту через 'listen=1' на TCP сокете
# Для надежной раздачи HTTP TS лучше поднять простой python сервер, а ffmpeg пусть пишет в pipe или файл
FIFO_PATH="${OUTPUT_DIR}/http_pipe.ts"
mkfifo "$FIFO_PATH" 2>/dev/null
ffmpeg -hide_banner -loglevel error -re -i "$SOURCE_URL" -c copy -f mpegts "$FIFO_PATH" -y &
echo "  -> HTTP TS/HLS сервер поднят на порту $HTTP_TS_PORT"

# 4. HLS
echo "  -> HLS Playlist:  $HLS_URL"
ffmpeg -hide_banner -loglevel error -re -i "$SOURCE_URL" -c copy -f hls -hls_time 5 -hls_list_size 5 -hls_flags delete_segments "$HLS_DIR/stream.m3u8" &

# Запускаем простой HTTP-сервер для отдачи HTTP_TS (через pipe) и HLS файлов
echo ""
echo "🚀 Трансляция начата. Нажмите [CTRL+C] для остановки."
echo "Вы можете использовать следующие URL для тестирования во вкладке Debug:"
echo "-----------------------------------------------------"
echo "1. UDP Multicast: udp://239.0.0.1:1234"
echo "2. UDP Unicast:   udp://127.0.0.1:1235"
echo "3. HTTP-TS (raw): $HTTP_TS_URL"
echo "4. HLS:           $HLS_URL"
echo "-----------------------------------------------------"

# Наш кастомный HTTP-сервер на Python для отдачи .ts и hls
python3 -c "
import http.server
import socketserver
import os
import shutil

PORT = $HTTP_TS_PORT
OUTPUT_DIR = '$OUTPUT_DIR'
FIFO_PATH = '$FIFO_PATH'

class HTTPTSHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUTPUT_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/stream.ts':
            self.send_response(200)
            self.send_header('Content-type', 'video/mp2t')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                # Читаем pipe и отдаем по HTTP
                with open(FIFO_PATH, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except (ConnectionResetError, BrokenPipeError):
                pass
        else:
            # Для HLS устанавливаем CORS
            self.send_response(200)
            if self.path.endswith('.m3u8'):
                self.send_header('Content-type', 'application/vnd.apple.mpegurl')
                self.send_header('Cache-Control', 'no-cache')
            elif self.path.endswith('.ts'):
                self.send_header('Content-type', 'video/mp2t')
            
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            file_path = os.path.join(OUTPUT_DIR, self.path.lstrip('/'))
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        shutil.copyfileobj(f, self.wfile)
                except BrokenPipeError:
                    pass

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('', PORT), HTTPTSHandler) as httpd:
    httpd.serve_forever()
"

wait
