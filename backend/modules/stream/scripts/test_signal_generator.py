#!/usr/bin/env python3
import subprocess
import time
import argparse
import os
import signal
import sys
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
    "rtmp": "rtmp://127.0.0.1:1935/test",
    "rtmps": "rtmps://127.0.0.1:1936/test_rtmps",
    "rtsp": "rtsp://127.0.0.1:8554/test",
    "hls": "http://127.0.0.1:8888/test/index.m3u8",
    "dash": "http://127.0.0.1:8888/test_dash/index.mpd",
    "srt": "srt://127.0.0.1:8890?streamid=read:test",
    "rist": "rist://127.0.0.1:5000",
    "tcp": "tcp://127.0.0.1:9001",
}

class TestSignalGenerator:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.mtx_process: subprocess.Popen = None

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
            return base_args + ["-f", "mpegts", url]
        elif proto == "rtp":
            return base_args + ["-f", "rtp_mpegts", url]
        elif proto == "http" or proto == "http_ts":
            return base_args + ["-f", "mpegts", "-listen", "1", url]
        elif proto == "rtmp":
            return base_args + ["-f", "flv", url]
        elif proto == "rtmps":
            return base_args + ["-f", "flv", "-tls_verify", "0", url]
        elif proto == "rtsp":
            return base_args + ["-f", "rtsp", "-muxdelay", "0.1", url]
        elif proto == "srt":
            srt_url = url if "streamid=publish" in url else url.replace("streamid=read", "streamid=publish")
            return base_args + ["-f", "mpegts", srt_url]
        elif proto == "hls":
            return base_args + ["-f", "flv", "rtmp://127.0.0.1:1935/test"]
        elif proto == "dash":
            return base_args + ["-f", "flv", "rtmp://127.0.0.1:1935/test_dash"]
        elif proto == "rist":
            return base_args + ["-f", "rist", url]
        elif proto == "tcp":
            return base_args + ["-f", "mpegts", f"{url}?listen"]
        
        return base_args + ["-f", "mpegts", url]

    def start_stream(self, proto: str):
        if proto not in STREAMS:
            print(f"[!] Неизвестный протокол: {proto}")
            return

        if proto in ["rtmp", "rtmps", "rtsp", "srt", "hls", "dash"]:
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
        for proto, proc in self.processes.items():
            proc.terminate()
        
        if self.mtx_process:
            self.mtx_process.terminate()
        
        print("[*] Готово.")

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
        for proto in STREAMS.keys():
            gen.start_stream(proto)
    else:
        gen.start_stream(args.protocol)

    print("[*] Генераторы запущены. Нажмите Ctrl+C для остановки.")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
