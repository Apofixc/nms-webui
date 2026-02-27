from __future__ import annotations

import time
import uuid
from typing import Any

from backend.modules.stream.core.types import StreamResult, StreamTask


def dict_to_task(payload: dict[str, Any]) -> StreamTask:
    """Конвертация старого dict запроса в StreamTask (preview по умолчанию)."""
    task_id = payload.get("id") or str(uuid.uuid4())
    return StreamTask(
        id=task_id,
        type=payload.get("type") or "preview",
        source_url=payload.get("url") or payload.get("source_url") or "",
        input_protocol=payload.get("input_protocol") or payload.get("input_format") or "http",
        output_format=payload.get("output_format") or payload.get("format") or "jpg",
        config=payload.get("config") or {},
        timeout_sec=int(payload.get("timeout_sec") or payload.get("timeout") or 30),
        created_at=payload.get("created_at") or time.time(),
    )


def result_to_dict(result: StreamResult) -> dict[str, Any]:
    return {
        "success": result.success,
        "path": result.output_path,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "metrics": result.metrics,
        "backend": result.backend_name,
    }
