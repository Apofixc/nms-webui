"""Astra stream backend (relay UDP to HTTP)."""
from __future__ import annotations

from typing import Any, AsyncGenerator, Optional

import httpx

from backend.stream.backends.base import StreamBackend
from backend.stream.backends.udp_to_http import parse_udp_url


class AstraStreamBackend(StreamBackend):
    name = "astra"
    input_types = {"udp_ts", "rtp", "file", "http"}
    output_types = {"http_ts"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        opts = options or {}
        relay_url = (opts.get("astra") or {}).get("relay_url") or ""
        return bool(str(relay_url).strip())

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[bytes, None]:
        try:
            _bind_addr, port, mcast = parse_udp_url(udp_url)
        except ValueError:
            return
        opts = options or {}
        base = ((opts.get("astra") or {}).get("relay_url") or "http://localhost:8000").strip().rstrip("/")
        addr = f"{mcast or '0.0.0.0'}:{port}"
        url = f"{base}/udp/{addr}"
        try:
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
            return
