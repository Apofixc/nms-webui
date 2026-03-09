#!/usr/bin/env python3
import subprocess
import time
import argparse
import os
import signal
import sys
import threading
import socket
from typing import Dict

# Настройки по умолчанию
MEDIAMTX_PATH = "/opt/mediamtx"
MEDIAMTX_CONF = "/opt/nms-webui/mediamtx.yml"

# Список потоков (теперь большинство идет через MediaMTX /test)
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

class TestSignalGenerator:
    def __init__(self):
        self.mtx_process: subprocess.Popen = None
        self.running = True
        self.threads = []
        
        # Релеи для специфичных форматов (HTTP/TCP), которые MediaMTX не отдает "как есть"
        self.relay_ports = {
            "http": (9080, 8080, True),
            "http_ts": (9081, 8081, True),
            "tcp": (9082, 1236, False)
        }
        # Вспомогательный FFmpeg для релеев
        self.relay_ffmpeg: subprocess.Popen = None

    def start_tcp_relay(self, name: str, udp_port: int, tcp_port: int, is_http: bool = False):
        def relay_worker():
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.bind(("127.0.0.1", udp_port))
            udp_sock.settimeout(1.0)

            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(("0.0.0.0", tcp_port))
            server_sock.listen(10)
            server_sock.settimeout(1.0)
            
            clients = []

            def accept_worker():
                while self.running:
                    try:
                        client, _ = server_sock.accept()
                        if is_http:
                            client.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: video/mp2t\r\n\r\n")
                        client.setblocking(False)
                        clients.append(client)
                    except socket.timeout: continue
                    except Exception: break

            threading.Thread(target=accept_worker, daemon=True).start()

            while self.running:
                try:
                    data, _ = udp_sock.recvfrom(65536)
                    for c in list(clients):
                        try: c.sendall(data)
                        except:
                            clients.remove(c)
                            c.close()
                except socket.timeout: continue
                except: break
            
            udp_sock.close()
            server_sock.close()

        t = threading.Thread(target=relay_worker, daemon=True)
        t.start()
        self.threads.append(t)

    def start_mediamtx(self):
        print(f"[*] Запуск MediaMTX...")
        self.mtx_process = subprocess.Popen([MEDIAMTX_PATH, MEDIAMTX_CONF])
        
        # Запускаем FFmpeg для релеев (питает локальные UDP порты 9080-9082)
        cmd = [
            "ffmpeg", "-re", "-i", "http://31.130.202.110/httpts/tv3by/avchigh.ts",
            "-c", "copy", "-f", "mpegts", "udp://127.0.0.1:9080?pkt_size=1316",
            "-c", "copy", "-f", "mpegts", "udp://127.0.0.1:9081?pkt_size=1316",
            "-c", "copy", "-f", "mpegts", "udp://127.0.0.1:9082?pkt_size=1316"
        ]
        self.relay_ffmpeg = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop_all(self):
        print("[*] Остановка...")
        self.running = False
        if self.mtx_process:
            self.mtx_process.terminate()
        if self.relay_ffmpeg:
            self.relay_ffmpeg.terminate()
        time.sleep(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("protocol", nargs="?", choices=list(STREAMS.keys()) + ["all"])
    args = parser.parse_args()

    if not args.protocol:
        parser.print_help()
        return

    gen = TestSignalGenerator()
    signal.signal(signal.SIGINT, lambda s, f: (gen.stop_all(), sys.exit(0)))

    # Запускаем MediaMTX (он сам поднимет большинство потоков через runOnInit)
    gen.start_mediamtx()

    # Запускаем релеи
    if args.protocol == "all":
        for name, params in gen.relay_ports.items():
            gen.start_tcp_relay(name, *params)
    elif args.protocol in gen.relay_ports:
        gen.start_tcp_relay(args.protocol, *gen.relay_ports[args.protocol])

    print("[*] Генератор (MediaMTX + Relays) запущен. Ctrl+C для выхода.")
    while True:
        if gen.mtx_process.poll() is not None:
            print("[!] MediaMTX упал, перезапуск...")
            gen.start_mediamtx()
        time.sleep(2)

if __name__ == "__main__":
    main()
