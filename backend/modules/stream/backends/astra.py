"""Astra stream backend: UDP → HTTP через Cesbo Astra.

Простая схема:
  1) Генерируем Lua-скрипт (make_channel: input=udp, output=http).
  2) Запускаем Astra с этим скриптом.
  3) Стримим HTTP-поток в mpegts.js.
  4) При отключении клиента завершаем процесс Astra.

Опционально: если задан relay_url (уже запущен astra --relay), просто запрашиваем {relay_url}/udp/{addr}.
"""
from __future__ import annotations

import asyncio
import re
import socket
import subprocess
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

import httpx

from backend.modules.stream.backends.base import StreamBackend
from backend.modules.stream.backends.udp_to_http import parse_udp_url
from backend.core.utils import find_executable


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _channel_name_from_url(url: str) -> str:
    s = (url or "").strip()
    if not s:
        return "HTTP_channel"
    s = re.sub(r"^[a-z]+://", "", s, flags=re.I)
    s = re.sub(r"[^a-zA-Z0-9._-]", "_", s)
    return ("HTTP_" + (s or "channel").strip("_"))[:64]


def _lua_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def _make_script(source_url: str, http_port: int, http_path: str, input_opts: str) -> str:
    name = _channel_name_from_url(source_url)
    path_clean = http_path.strip("/") or "stream"
    inp = source_url.rstrip("/")
    if input_opts and not inp.endswith("#"):
        inp = inp + input_opts
    out = f"http://0:{http_port}/{path_clean}#keep_active"
    return f'''make_channel({{
  name = "{_lua_escape(name)}",
  input =  {{ "{_lua_escape(inp)}", }},
  output = {{ "{_lua_escape(out)}", }}
}})
'''


class AstraStreamBackend(StreamBackend):
    name = "astra"
    input_types = {"udp_ts", "rtp", "file", "http"}
    output_types = {"http_ts"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        opts = options or {}
        a = opts.get("astra") or {}
        bin_name = (a.get("bin") or "astra").strip()
        return find_executable(bin_name) is not None

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[bytes, None]:
        opts = options or {}
        a = opts.get("astra") or {}

        # Режим скрипта: создать скрипт → запустить Astra → отдавать HTTP → по выходу закрыть Astra
        try:
            _bind_addr, _port, _mcast = parse_udp_url(udp_url)
        except ValueError:
            return

        astra_bin = find_executable((a.get("bin") or "astra").strip())
        if not astra_bin:
            return

        http_port = int(a.get("http_port") or 0) or _free_port()
        http_path = (a.get("http_path") or "stream").strip().strip("/") or "stream"
        input_opts = (a.get("input_opts") or "#filter=0").strip()

        script_body = _make_script(udp_url, http_port, http_path, input_opts)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".lua", delete=False, encoding="utf-8") as f:
            f.write(script_body)
            script_path = f.name

        proc = None
        try:
            proc = subprocess.Popen(
                [astra_bin, script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            await asyncio.sleep(1.5)

            url = f"http://127.0.0.1:{http_port}/{http_path}"
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                async with client.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        return
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        try:
                            if await request.is_disconnected():
                                return
                        except Exception:
                            pass
                        yield chunk
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError):
            pass
        finally:
            try:
                Path(script_path).unlink(missing_ok=True)
            except Exception:
                pass
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
