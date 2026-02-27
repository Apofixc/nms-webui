from __future__ import annotations

import asyncio
import socket
import threading
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import StreamResult, StreamTask


def _free_port() -> int:
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_http_passthrough(source_url: str) -> tuple[ThreadingHTTPServer, str]:
    """Запускает минимальный http->http прокси в отдельном потоке."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # type: ignore[override]
            try:
                with urllib.request.urlopen(source_url, timeout=5) as resp:
                    self.send_response(200)
                    ct = resp.headers.get("Content-Type") or "application/octet-stream"
                    self.send_header("Content-Type", ct)
                    self.end_headers()
                    while True:
                        chunk = resp.read(64 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except Exception as exc:  # pragma: no cover - сеть может упасть
                self.send_error(502, str(exc))

        def log_message(self, fmt, *args):  # pragma: no cover - тишина
            return

    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}/"


def _start_udp_to_http(udp_url: str) -> tuple[ThreadingHTTPServer, str, threading.Thread, socket.socket]:
    """UDP→HTTP: читает датаграммы и отдаёт через HTTP chunked."""
    parsed = urllib.parse.urlparse(udp_url)
    host, port = parsed.hostname, parsed.port
    if not host or not port:
        raise ValueError("Invalid udp url")
    queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1024)

    def udp_reader(sock: socket.socket):
        sock.settimeout(1.0)
        while True:
            try:
                data = sock.recv(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                continue
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                continue

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # type: ignore[override]
            self.send_response(200)
            self.send_header("Content-Type", "video/MP2T")
            self.end_headers()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                while True:
                    try:
                        chunk = loop.run_until_complete(asyncio.wait_for(queue.get(), timeout=2.0))
                    except asyncio.TimeoutError:
                        break
                    self.wfile.write(chunk)
            finally:
                loop.close()

        def log_message(self, fmt, *args):  # pragma: no cover
            return

    port_http = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port_http), Handler)
    t_srv = threading.Thread(target=server.serve_forever, daemon=True)
    t_srv.start()
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("", port))
    t_udp = threading.Thread(target=udp_reader, args=(udp_sock,), daemon=True)
    t_udp.start()
    return server, f"http://127.0.0.1:{port_http}/", t_udp, udp_sock


class PureProxyBackend(IStreamBackend):
    """Чисто-Python прокси: http->http, hls->hls, udp->http без внешних бинарей."""

    def __init__(self):
        self._servers: list[ThreadingHTTPServer] = []
        self._threads: list[threading.Thread] = []
        self._sockets: list[socket.socket] = []

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "protocols": ["http", "hls", "udp"],
            "outputs": ["http_ts", "http_hls"],
            "features": ["python_only", "proxy"],
            "priority_matrix": {
                "http": {"http_ts": 50, "http_hls": 50},
                "hls": {"http_hls": 60},
                "udp": {"http_ts": 40},
            },
        }

    def match_score(self, input_proto: str, output_format: str) -> int:
        caps = self.get_capabilities()
        if input_proto in caps.get("protocols", []) and output_format in caps.get("outputs", []):
            return int((caps.get("priority_matrix", {}).get(input_proto, {}) or {}).get(output_format, 10))
        return 0

    async def initialize(self, config: dict[str, Any]) -> bool:
        return True

    async def health_check(self) -> bool:
        return True

    async def shutdown(self) -> None:
        for srv in self._servers:
            try:
                srv.shutdown()
            except Exception:
                pass
        self._servers.clear()
        for s in self._sockets:
            try:
                s.close()
            except Exception:
                pass
        self._sockets.clear()
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=0.5)
        self._threads.clear()

    async def process(self, task: StreamTask) -> StreamResult:
        proto = (task.input_protocol or "").lower()
        # HTTP/HLS → HTTP/HLS
        if proto in {"http", "https", "hls"}:
            srv, url = _start_http_passthrough(task.source_url)
            self._servers.append(srv)
            return StreamResult(success=True, output_path=url, backend_name="pure_proxy")

        # UDP → HTTP TS
        if proto.startswith("udp"):
            srv, url, t_udp, sock = _start_udp_to_http(task.source_url)
            self._servers.append(srv)
            self._threads.append(t_udp)
            self._sockets.append(sock)
            return StreamResult(success=True, output_path=url, backend_name="pure_proxy")

        return StreamResult(success=False, output_path=None, error_code="UNSUPPORTED", error_message="protocol not supported", backend_name="pure_proxy")
