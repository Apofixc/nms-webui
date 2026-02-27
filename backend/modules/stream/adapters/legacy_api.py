from __future__ import annotations

import asyncio
from typing import Any
from backend.modules.stream.adapters.type_converters import dict_to_task, result_to_dict
from backend.modules.stream.core.pipeline import Pipeline, run_task_sync
from backend.modules.stream.core.types import StreamResult, StreamTask

_pipeline = Pipeline()


async def _capture_frame_async(url: str, *, timeout: int = 10, quality: int = 80) -> dict[str, Any]:
    task = StreamTask(
        id="",  # заполняется в dict_to_task при необходимости
        type="preview",
        source_url=url,
        input_protocol="http",
        output_format="jpg",
        config={"quality": quality},
        timeout_sec=timeout,
        created_at=0.0,
    )
    result: StreamResult = await _pipeline.process(task)
    return result_to_dict(result)


def capture_frame(url: str, timeout: int = 10, quality: int = 80) -> dict[str, Any]:
    """Старый API: синхронный захват кадра."""
    return run_task_sync(_capture_frame_async(url, timeout=timeout, quality=quality))


async def submit_preview_task(payload: dict[str, Any]) -> dict[str, Any]:
    task = dict_to_task(payload)
    result: StreamResult = await _pipeline.process(task)
    return result_to_dict(result)
