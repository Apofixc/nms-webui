#!/usr/bin/env python3
import subprocess
import time
import argparse
import os
import signal
import sys
import shutil
import threading
import socket
from typing import List, Dict

# Настройки по умолчанию
MEDIAMTX_PATH = "/opt/mediamtx"
MEDIAMTX_CONF = "/opt/nms-webui/mediamtx.yml"
FFMPEG_PATH = "ffmpeg"

# Список потоков для генерации (точки чтения)
STREAMS = {
    "udp": "udp://239.0.0.1:1234",
    "rtp": "rtp://239.0.0.1:1235",
    "http": "http://127.0.0.1:8080/test",
    "http_ts": "http://127.0.0.1:8081/test.ts",
    "rtmp": "rtmp://127.0.0.1:1935/test_rtmp",
    "rtsp": "rtsp://127.0.0.1:8554/test_rtsp",
    "hls": "http://127.0.0.1:8888/test_hls/index.m3u8",
    "srt": "srt://127.0.0.1:8890?streamid=read:test_srt",
    "tcp": "tcp://127.0.0.1:1236",
    # Для многоадресной раздачи RIST используем multicast IP
    "rist": "rist://239.0.0.2:1238",
}

class TestSignalGenerator:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.mtx_process: subprocess.Popen = None
        self.running = True
        
        # Локальный TCP-релей для обхода ограничения ffmpeg listen=1 (HTTP и TCP)
        self.http_port = 8080
        self.http_ts_port = 8081
        self.tcp_port = 1236
        self.relay_ports = {
            "http": (9080, self.http_port, True),       # (udp_in, tcp_out, send_http_headers)
            "http_ts": (9081, self.http_ts_port, True),
            "tcp": (9082, self.tcp_port, False)
        }
        self.threads = []

    def start_tcp_relay(self, name: str, udp_port: int, tcp_port: int, is_http: bool = False):
        """Простой TCP сервер, который читает UDP и рассылает всем подключенным TCP клиентам."""
        def relay_worker():
            # UDP сокет для приема потока от ffmpeg
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.bind(("127.0.0.1", udp_port))
            udp_sock.settimeout(1.0)

            # TCP сервер для клиентов
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(("0.0.0.0", tcp_port))
            server_sock.listen(100)
            server_sock.settimeout(1.0)
            
            clients = []
            
            # Поток для принятия новых клиентов
            def accept_worker():
                while self.running:
                    try:
                        client, addr = server_sock.accept()
                        
                        if is_http:
                            # Отправляем фейковый HTTP ответ
                            response = b"HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Type: video/mp2t\r\nCache-Control: no-cache\r\n\r\n"
                            client.sendall(response)
                        
                        client.setblocking(False)
                        clients.append(client)
                        print(f"[{name}] Новый клиент подключен: {addr}")
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.running:
                            print(f"[{name}] Ошибка accept: {e}")

            accept_thread = threading.Thread(target=accept_worker, daemon=True)
            accept_thread.start()

            print(f"[*] Запущен локальный HTTP/TS мост для {name} на порту {tcp_port}")

            # Основной цикл рассылки UDP -> TCP клиенты
            while self.running:
                try:
                    data, _ = udp_sock.recvfrom(65536)
                    dead_clients = []
                    for c in clients:
                        try:
                            c.sendall(data)
                        except Exception:
                            dead_clients.append(c)
                            
                    for c in dead_clients:
                        clients.remove(c)
                        try:
                            c.close()
                        except:
                            pass
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[{name}] Ошибка relay: {e}")
                        
            udp_sock.close()
            server_sock.close()

        t = threading.Thread(target=relay_worker, daemon=True)
        t.start()
        self.threads.append(t)

    def start_mediamtx(self):
        if self.mtx_process and self.mtx_process.poll() is None:
            return
        
        print(f"[*] Запуск MediaMTX ({MEDIAMTX_PATH})...")
        try:
            self.mtx_process = subprocess.Popen(
                [MEDIAMTX_PATH, MEDIAMTX_CONF],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(2)  # Даем время на запуск
        except Exception as e:
            print(f"[!] Ошибка запуска MediaMTX: {e}")

    def get_ffmpeg_cmd(self, proto: str, url: str) -> List[str]:
        # Базовый генератор: тестовая таблица + синусоида
        base_args = [
            FFMPEG_PATH, "-re",
            "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=44100",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
            "-profile:v", "baseline", "-level", "3.0",
            "-g", "25", "-keyint_min", "25", "-sc_threshold", "0",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
        ]

        if proto == "udp":
            return base_args + [
                "-f", "mpegts",
                "-pkt_size", "1316",
                f"{url}?fifo_size=100000&overrun_nonfatal=1"
            ]
                
        elif proto == "rtp":
            return base_args + [
                "-f", "rtp_mpegts",
                "-pkt_size", "1316",
                "-fflags", "+nobuffer+genpts",
                "-max_delay", "500000",
                # RTP поверх UDP: те же буферные настройки
                f"{url}?pkt_size=1316&buffer_size=655360&timeout=5000000"
            ]
        
        elif proto == "http":
            udp_port = self.relay_ports["http"][0]
            return base_args + ["-f", "mpegts", f"udp://127.0.0.1:{udp_port}?pkt_size=1316"]
        
        elif proto == "http_ts":
            udp_port = self.relay_ports["http_ts"][0]
            return base_args + ["-f", "mpegts", f"udp://127.0.0.1:{udp_port}?pkt_size=1316"]
        
        elif proto == "tcp":
            udp_port = self.relay_ports["tcp"][0]
            return base_args + ["-f", "mpegts", f"udp://127.0.0.1:{udp_port}?pkt_size=1316"]
        
        elif proto == "rist":
            rist_url = url if "streamid=publish" in url else url.replace("streamid=read", "streamid=publish")
            return base_args + [
                "-f", "mpegts",
                "-mpegts_flags", "+resend_headers",
                "-mpegts_service_id", "1",
                "-rist_profile", "simple",
                #"-buffer_size", "4000",         # [ИЗМ] Увеличен буфер (4 сек)
                #"-fifo_size", "32768",          # [ИЗМ] Увеличен FIFO (32k)
                "-pkt_size", "1316",
                "-reconnect", "1",              # [НОВОЕ] Авто-переподключение
                "-reconnect_delay_max", "5",    # [НОВОЕ] Макс. задержка переподключения
                rist_url
            ]

        elif proto == "rtmp":
            return base_args + ["-f", "flv", url]
        
        elif proto == "rtsp":
            return base_args + ["-f", "rtsp", "-muxdelay", "0.1", url]
        
        elif proto == "srt":
            srt_url = url if "streamid=publish" in url else url.replace("streamid=read", "streamid=publish")
            return base_args + ["-f", "mpegts", srt_url]
        
        elif proto == "hls":
            hls_rtmp_url = url.replace("http://", "rtmp://").replace("/index.m3u8", "").replace(":8888", ":1935")
            return base_args + ["-f", "flv", hls_rtmp_url]
        

        return base_args + ["-f", "mpegts", url]

    def start_stream(self, proto: str):
        if proto not in STREAMS:
            print(f"[!] Неизвестный протокол: {proto}")
            return

        # Для HLS и других MediaMTX протоколов
        if proto in ["rtmp", "rtsp", "srt", "hls"]:
            self.start_mediamtx()

        url = STREAMS[proto]
        cmd = self.get_ffmpeg_cmd(proto, url)
        
        print(f"[*] Запуск потока {proto.upper()}: {url}")
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.processes[proto] = proc
        except Exception as e:
            print(f"[!] Ошибка запуска FFmpeg для {proto}: {e}")

    def stop_all(self):
        print("[*] Остановка всех процессов...")
        self.running = False
        
        # 1. Сначала гасим основные ffmpeg-генераторы
        for proto, proc in self.processes.items():
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
            except Exception as e:
                print(f"[!] Ошибка остановки {proto}: {e}")
        
        # 2. Гасим MediaMTX
        if self.mtx_process:
            try:
                if self.mtx_process.poll() is None:
                    self.mtx_process.terminate()
                    try:
                        self.mtx_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.mtx_process.kill()
                        self.mtx_process.wait()
            except Exception as e:
                print(f"[!] Ошибка остановки MediaMTX: {e}")
        
        # 3. Даем время потокам релея закрыть сокеты (они проверяют self.running)
        time.sleep(1.2)
        
        print("[*] Готово.")

    def check_and_restart(self):
        """Проверка живы ли процессы и перезапуск при необходимости.
        Особенно важно для HTTP/TCP с ключом -listen 1, которые выходят после 1 клиента.
        """
        for proto, proc in list(self.processes.items()):
            if proc.poll() is not None:
                # Процесс завершился (например, клиент отключился от ffmpeg -listen 1)
                # Перезапускаем его
                self.start_stream(proto)

def main():
    parser = argparse.ArgumentParser(description="Генератор тестовых сигналов NMS-WebUI")
    parser.add_argument("protocol", nargs="?", choices=list(STREAMS.keys()) + ["all"], help="Протокол для тестирования")
    parser.add_argument("--list", action="store_true", help="Показать список доступных потоков")
    
    args = parser.parse_args()

    if args.list:
        print("Доступные потоки:")
        for k, v in STREAMS.items():
            print(f"  {k:8} : {v}")
        return

    if not args.protocol:
        parser.print_help()
        return

    gen = TestSignalGenerator()

    def signal_handler(sig, frame):
        gen.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    if args.protocol == "all":
        # Запускаем relay для HTTP и TCP протоколов
        gen.start_tcp_relay("http", *gen.relay_ports["http"])
        gen.start_tcp_relay("http_ts", *gen.relay_ports["http_ts"])
        gen.start_tcp_relay("tcp", *gen.relay_ports["tcp"])
        
        for proto in STREAMS.keys():
            gen.start_stream(proto)
    else:
        if args.protocol in ["http", "http_ts", "tcp"]:
            gen.start_tcp_relay(args.protocol, *gen.relay_ports[args.protocol])
        gen.start_stream(args.protocol)

    print("[*] Генераторы запущены. Нажмите Ctrl+C для остановки.")
    while True:
        gen.check_and_restart()
        time.sleep(1)

if __name__ == "__main__":
    main()
