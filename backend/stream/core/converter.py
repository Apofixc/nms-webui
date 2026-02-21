"""UniversalStreamConverter: single entry point to resolve backend and stream or start HLS."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from backend.stream.core.registry import (
    STREAM_BACKENDS_BY_NAME,
    get_backend_for_link,
)


class UniversalStreamConverter:
    """
    Facade: given (url, input_format, output_format, options) resolve backend via registry,
    then either yield bytes (HTTP-TS) or start HLS and return (session_dir, process).
    """

    @staticmethod
    def get_backend_name(
        preference: str,
        input_format: str,
        output_format: str,
        options: Optional[dict[str, Any]] = None,
    ) -> str:
        """Resolve backend name for the link. Raises ValueError if none available."""
        return get_backend_for_link(preference, input_format, output_format, options)

    @staticmethod
    def get_backend_class(backend_name: str):
        """Get backend class by name."""
        return STREAM_BACKENDS_BY_NAME.get(backend_name)

    @staticmethod
    async def stream(
        url: str,
        request: Any,
        backend_name: str,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        """Stream URL to request using the given backend. Yields bytes (HTTP-TS)."""
        backend_cls = STREAM_BACKENDS_BY_NAME.get(backend_name)
        if not backend_cls:
            raise ValueError(f"Unknown backend: {backend_name}")
        async for chunk in backend_cls.stream(url, request, options):
            yield chunk

    @staticmethod
    def start_hls_sync(
        url: str,
        session_dir: Path,
        backend_name: str,
        options: Optional[dict[str, Any]] = None,
    ):
        """Start HLS process synchronously. Returns subprocess.Popen."""
        backend_cls = STREAM_BACKENDS_BY_NAME.get(backend_name)
        if not backend_cls:
            raise ValueError(f"Unknown backend: {backend_name}")
        start_hls_fn = getattr(backend_cls, "start_hls", None)
        if not callable(start_hls_fn):
            raise NotImplementedError(f"Backend {backend_name!r} does not support HLS")
        return start_hls_fn(url, session_dir, options)

    @staticmethod
    async def start_hls_async(
        url: str,
        session_dir: Path,
        backend_name: str,
        options: Optional[dict[str, Any]] = None,
    ):
        """Start HLS process in thread. Returns subprocess.Popen."""
        return await asyncio.to_thread(
            UniversalStreamConverter.start_hls_sync,
            url,
            session_dir,
            backend_name,
            options,
        )
