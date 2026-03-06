import logging
import shutil
from typing import Any, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import AstraStreamer

logger = logging.getLogger(__name__)

class AstraBackend(IStreamBackend):
    """Бэкенд на базе Cesbo Astra."""

    def __init__(self, settings: dict, manifest: dict):
        self._settings = settings
        self._manifest = manifest
        self._streamer = AstraStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "astra"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        formats = self._manifest.get("formats", {})
        protos = formats.get("input_protocols", [])
        result = set()
        for p in protos:
            try:
                result.add(StreamProtocol(p.lower()))
            except ValueError:
                pass
        
        if not result:
            return {StreamProtocol.UDP, StreamProtocol.RTP}
        return result

    def supported_output_types(self) -> Set[OutputType]:
        formats = self._manifest.get("formats", {})
        types = formats.get("output_types", [])
        result = set()
        for t in types:
            try:
                result.add(OutputType(t.lower()))
            except ValueError:
                pass
        
        if not result:
            return {OutputType.HTTP, OutputType.HTTP_TS}
        return result

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        return await self._streamer.stop(task_id)

    def get_process(self, task_id: str) -> Optional[Any]:
        return self._streamer.get_process(task_id)

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        return self._streamer.get_playback_info(task_id)

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return None

    async def is_available(self) -> bool:
        astra_path = self._settings.get("binary_path", "astra")
        return shutil.which(astra_path) is not None

    async def health_check(self) -> dict:
        return {
            "backend": "astra",
            "available": await self.is_available(),
            "active_processes": self._streamer.get_active_count(),
            "binary": self._settings.get("binary_path", "astra")
        }

    async def set_signaling_answer(self, task_id: str, sdp: str, sdp_type: str) -> bool:
        return False

    async def get_dynamic_cost(self, protocol: StreamProtocol) -> float:
        count = self._streamer.get_active_count()
        return 4.0 + (count * 1.5)


def create_backend(settings: Any, manifest: Optional[dict] = None) -> IStreamBackend:
    if hasattr(settings, "manifest") and manifest is None:
        actual_manifest = settings.manifest
        actual_settings = settings.manifest.get("config", {})
    else:
        actual_manifest = manifest or {}
        actual_settings = settings if isinstance(settings, dict) else {}
        
    return AstraBackend(settings=actual_settings, manifest=actual_manifest)
