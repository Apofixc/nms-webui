"""UniversalStreamConverter: single entry point to resolve backend and stream or start HLS."""
from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from backend.modules.stream.core.registry import (
    STREAM_BACKENDS_BY_NAME,
    get_backend_for_link,
)
from backend.modules.stream.core.types import StreamConfig

logger = logging.getLogger(__name__)


class UniversalStreamConverter:
    """
    Facade: given (url, input_format, output_format, options) resolve backend via registry,
    then either yield bytes (HTTP-TS) or start HLS and return (session_dir, process).
    Supports both static API and instance API with StreamConfig.
    """

    def __init__(self, config: StreamConfig) -> None:
        self._config = config
        self._backend_name: Optional[str] = None
        self._hls_process: Optional[Any] = None
        self._hls_dir: Optional[Path] = None

    @property
    def config(self) -> StreamConfig:
        return self._config

    @property
    def backend_name(self) -> Optional[str]:
        return self._backend_name

    def start(self) -> str:
        """
        Resolve backend by registry and store backend name. Call before stream() or start_hls().
        Returns resolved backend name.
        """
        preference = (self._config.backend or "auto").strip() or "auto"
        opts = self._config.backend_options or {}
        self._backend_name = get_backend_for_link(
            preference,
            self._config.input_format,
            self._config.output_format,
            opts,
        )
        logger.info("stream converter started backend=%s input=%s output=%s", 
                    self._backend_name, self._config.input_format, self._config.output_format)
        return self._backend_name

    async def stream(self, request: Any) -> AsyncIterator[bytes]:
        """Stream source to request using resolved backend (HTTP-TS). Call start() first."""
        if self._backend_name is None:
            self.start()
        backend_cls = STREAM_BACKENDS_BY_NAME.get(self._backend_name)
        if not backend_cls:
            raise ValueError(f"Unknown backend: {self._backend_name}")
        opts = self._config.backend_options or {}
        async for chunk in backend_cls.stream(self._config.source_url, request, opts):
            yield chunk

    def start_hls_sync(self, session_dir: Path) -> Any:
        """Start HLS process synchronously. Stores process for stop(). Returns subprocess.Popen."""
        if self._backend_name is None:
            self.start()
        backend_cls = STREAM_BACKENDS_BY_NAME.get(self._backend_name)
        if not backend_cls:
            raise ValueError(f"Unknown backend: {self._backend_name}")
        start_hls_fn = getattr(backend_cls, "start_hls", None)
        if not callable(start_hls_fn):
            raise NotImplementedError(f"Backend {self._backend_name!r} does not support HLS")
        opts = self._config.backend_options or {}
        self._hls_dir = session_dir
        self._hls_process = start_hls_fn(self._config.source_url, session_dir, opts)
        return self._hls_process

    async def start_hls_async(self, session_dir: Path) -> Any:
        """Start HLS process in thread. Stores process for stop(). Returns subprocess.Popen."""
        return await asyncio.to_thread(self.start_hls_sync, session_dir)

    def stop(self, timeout: float = 5.0) -> None:
        """
        Stop any running HLS process and release resources. Safe to call multiple times.
        Guarantees cleanup on normal and abnormal termination.
        """
        if self._hls_process is not None:
            try:
                if self._hls_process.poll() is None:
                    self._hls_process.terminate()
                    self._hls_process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    self._hls_process.kill()
                except Exception:
                    pass
            except Exception:
                try:
                    self._hls_process.kill()
                except Exception:
                    pass
            self._hls_process = None
        self._hls_dir = None
        if self._backend_name:
            logger.info("stream converter stopped backend=%s", self._backend_name)

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
