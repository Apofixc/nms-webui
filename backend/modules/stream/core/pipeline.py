"""Конвейер обработки: цепочка шагов (например UDP -> HTTP-TS или UDP -> proxy -> HLS)."""
from __future__ import annotations

from typing import Any, AsyncIterator, List, Optional

from backend.modules.stream.core.registry import STREAM_BACKENDS_BY_NAME, get_backend_for_link


class PipelineStep:
    """Один шаг конвейера: имя бэкенда и пара (input_format, output_format)."""

    def __init__(self, backend_name: str, input_format: str, output_format: str):
        self.backend_name = backend_name
        self.input_format = input_format
        self.output_format = output_format

    @property
    def backend_cls(self):
        return STREAM_BACKENDS_BY_NAME.get(self.backend_name)


def build_single_backend_chain(
    preference: str,
    input_format: str,
    output_format: str,
    options: Optional[dict[str, Any]] = None,
) -> List[PipelineStep]:
    """
    По предпочтению и связке (input_format, output_format) вернуть цепочку из одного шага.
    Позже можно расширить для цепочек вида udp_proxy -> ffmpeg HLS.
    """
    backend_name = get_backend_for_link(preference, input_format, output_format, options)
    return [PipelineStep(backend_name, input_format, output_format)]
