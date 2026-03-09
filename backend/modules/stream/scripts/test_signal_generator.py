#!/usr/bin/env python3
import asyncio
import subprocess
import argparse
import os
import signal
import sys
import time
from typing import Dict, List

# Настройки по умолчанию
MEDIAMTX_PATH = "/opt/mediamtx"
MEDIAMTX_CONF = "/opt/nms-webui/mediamtx.yml"

# Список протоколов
STREAMS = {
    "udp": "udp://239.0.0.1:1234",
    "rtp": "rtp://239.0.0.1:1235",
    "rtmp": "rtmp://127.0.0.1:1935/test",
    "rtsp": "rtsp://127.0.0.1:8554/test",
    "hls": "http://127.0.0.1:8888/test/index.m3u8",
    "srt": "srt://127.0.0.1:8890?streamid=read:test",
    "rist": "rist://239.0.0.2:1238",
    "http": "http://127.0.0.1:8080/test",
    "http_ts": "http://127.0.0.1:8081/test.ts",
    "tcp": "tcp://127.0.0.1:1236",
}

class AsyncTestSignalGenerator:
    def __init__(self):
        self.mtx_process: subprocess.Popen = None
        self.running = True
        self.client_queues: List[asyncio.Queue] = []
        
        # Релеи (внешние порты)
        self.relay_ports = {
            "http": (8080, True),
            "http_ts": (8081, True),
            "tcp": (1236, False)
        }
        # Внутренний источник (TCP порт MediaMTX)
        self.internal_source_port = 9180

    async def source_reader(self):
        """Асинхронное чтение из мастер-источника (MediaMTX TCP) и раздача очередям."""
        print(f"[*] Подключение к внутреннему TCP источнику 127.0.0.1:{self.internal_source_port}...")
        while self.running:
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", self.internal_source_port)
                print("[*] Соединение с внутренним источником установлено (async).")
                
                while self.running:
                    data = await reader.read(131072)
                    if not data:
                        print("[!] Источник закрыл соединение.")
                        break
                    
                    # Рассылаем данные всем активным очередям
                    for q in list(self.client_queues):
                        try:
                            q.put_nowait(data)
                        except asyncio.QueueFull:
                            # Если клиент тормозит - очищаем самое старое и добавляем новое (или просто пропускаем)
                            pass
                
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                if self.running:
                    print(f"[!] Ошибка чтения из источника: {e}. Переподключение через 1с...")
                    await asyncio.sleep(1)
                continue

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, is_http: bool):
        """Обработка одного внешнего клиента (VLC, Chrome, etc)."""
        addr = writer.get_extra_info('peername')
        
        # Если это HTTP, ждем GET запрос перед отправкой заголовка
        if is_http:
            try:
                line = await reader.read(1024)
                if b"GET" in line:
                    writer.write(b"HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Type: video/mp2t\r\n\r\n")
                    await writer.drain()
            except Exception as e:
                print(f"[!] Ошибка HTTP хендшейка {addr}: {e}")
                writer.close()
                return

        # Создаем очередь для клиента
        q = asyncio.Queue(maxsize=100)
        self.client_queues.append(q)
        
        try:
            while self.running:
                data = await q.get()
                writer.write(data)
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError, Exception):
            pass
        finally:
            if q in self.client_queues:
                self.client_queues.remove(q)
            writer.close()
            try: await writer.wait_closed()
            except: pass

    async def start_relays(self):
        """Запуск асинхронных серверов для каждого порта релея."""
        servers = []
        for name, (port, is_http) in self.relay_ports.items():
            print(f"[*] Запуск {name} сервера на порту {port}...")
            server = await asyncio.start_server(
                lambda r, w, h=is_http: self.handle_client(r, w, h),
                "0.0.0.0", port
            )
            servers.append(server.serve_forever())
        
        # Запускаем чтец из источника и все серверы параллельно
        await asyncio.gather(self.source_reader(), *servers)

    def start_mediamtx(self):
        print(f"[*] Запуск MediaMTX...")
        self.mtx_process = subprocess.Popen([MEDIAMTX_PATH, MEDIAMTX_CONF])
        
    def stop_all(self):
        print("[*] Остановка...")
        self.running = False
        if self.mtx_process:
            self.mtx_process.terminate()

    async def run(self, protocol_arg: str):
        self.start_mediamtx()
        
        # Мониторинг MediaMTX в фоне
        async def monitor_mtx():
            while self.running:
                if self.mtx_process.poll() is not None:
                    print("[!] MediaMTX упал, перезапуск...")
                    self.start_mediamtx()
                await asyncio.sleep(2)

        asyncio.create_task(monitor_mtx())
        
        print("[*] Генератор (Asyncio + MediaMTX) запущен. Ctrl+C для выхода.")
        await self.start_relays()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("protocol", nargs="?", choices=list(STREAMS.keys()) + ["all"])
    args = parser.parse_args()

    if not args.protocol:
        parser.print_help()
        return

    gen = AsyncTestSignalGenerator()
    
    # Обработка сигналов
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: (gen.stop_all(), sys.exit(0)))

    try:
        loop.run_until_complete(gen.run(args.protocol))
    except KeyboardInterrupt:
        pass
    finally:
        gen.stop_all()

if __name__ == "__main__":
    main()
