from __future__ import annotations

import asyncio
import base64
import socket
import urllib.request
import urllib.parse
import base64 as _b64
from pathlib import Path
from typing import Any

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import StreamResult, StreamTask


_DUMMY_PNG = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/woAAn8B9fHnG6cAAAAASUVORK5CYII="
)


class PurePreviewBackend(IStreamBackend):
    """Чисто-Python превью: http(s) image fetch; stub png fallback for rtsp/udp."""

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "protocols": ["http", "https", "rtsp", "udp"],
            "outputs": ["jpg", "png"],
            "features": ["python_only", "preview"],
            "priority_matrix": {
                "http": {"jpg": 40, "png": 40},
                "https": {"jpg": 40, "png": 40},
                "rtsp": {"jpg": 20},
                "udp": {"jpg": 15},
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
        return None

    async def _save_bytes(self, data: bytes, path: Path) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, path.write_bytes, data)

    async def process(self, task: StreamTask) -> StreamResult:
        out_dir = Path("/tmp")
        out_dir.mkdir(parents=True, exist_ok=True)
        ext = task.output_format or "jpg"
        out_path = out_dir / f"{task.id}.{ext}"

        proto = (task.input_protocol or "").lower()

        # data: URI
        if task.source_url.startswith("data:image"):
            try:
                header, b64data = task.source_url.split(",", 1)
                data = _b64.b64decode(b64data)
                await self._save_bytes(data, out_path)
                return StreamResult(success=True, output_path=str(out_path), backend_name="pure_preview", metrics={"data_uri": True})
            except Exception as exc:
                return StreamResult(success=False, output_path=None, error_code="DATA_URI_ERROR", error_message=str(exc), backend_name="pure_preview")

        # file://
        if task.source_url.startswith("file://"):
            try:
                path = Path(task.source_url.removeprefix("file://"))
                data = path.read_bytes()
                await self._save_bytes(data, out_path)
                return StreamResult(success=True, output_path=str(out_path), backend_name="pure_preview", metrics={"file": True})
            except Exception as exc:
                return StreamResult(success=False, output_path=None, error_code="FILE_ERROR", error_message=str(exc), backend_name="pure_preview")

        # HTTP(S) image fetch (JPEG/PNG)
        if proto in {"http", "https"}:
            try:
                with urllib.request.urlopen(task.source_url, timeout=task.timeout_sec or 10) as resp:
                    ct = (resp.headers.get("Content-Type") or "").lower()
                    if "image" not in ct:
                        return StreamResult(
                            success=False,
                            output_path=None,
                            error_code="NOT_IMAGE",
                            error_message=f"Content-Type {ct}",
                            backend_name="pure_preview",
                        )
                    data = resp.read()
                await self._save_bytes(data, out_path)
                return StreamResult(success=True, output_path=str(out_path), backend_name="pure_preview")
            except Exception as exc:
                return StreamResult(success=False, output_path=None, error_code="HTTP_ERROR", error_message=str(exc), backend_name="pure_preview")

        # UDP MJPEG quick scan
        if proto.startswith("udp"):
            sock: socket.socket | None = None
            try:
                parsed = urllib.parse.urlparse(task.source_url)
                host, port = parsed.hostname, parsed.port
                if host and port:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.settimeout(min(3, task.timeout_sec or 3))
                    sock.bind(("", port))
                    data = b""
                    for _ in range(20):
                        try:
                            pkt, _ = sock.recvfrom(8192)
                        except socket.timeout:
                            continue
                        except OSError:
                            break
                        data += pkt
                        if b"\xff\xd8" in data and b"\xff\xd9" in data:
                            start = data.find(b"\xff\xd8")
                            end = data.find(b"\xff\xd9", start)
                            if end != -1:
                                frame = data[start : end + 2]
                                await self._save_bytes(frame, out_path)
                                return StreamResult(success=True, output_path=str(out_path), backend_name="pure_preview", metrics={"mjpeg": True})
                        if b"\x00\x00\x00\x01\x65" in data or b"\x00\x00\x01\x65" in data:
                            # Простая эвристика H264 IDR: сохраняем сырые данные
                            await self._save_bytes(data, out_path.with_suffix(".h264"))
                            return StreamResult(success=True, output_path=str(out_path.with_suffix('.h264')), backend_name="pure_preview", metrics={"h264_raw": True})
            except Exception:
                pass
            finally:
                if sock:
                    sock.close()

        # RTSP/h264 or no image found -> dummy
        await self._save_bytes(_DUMMY_PNG, out_path)
        return StreamResult(success=True, output_path=str(out_path), backend_name="pure_preview", metrics={"stub": True})
