from __future__ import annotations

import asyncio
import logging
import uuid
import shutil
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.core.stream import (
    capture_frame,
    get_heavy_semaphores,
    get_preview_cache_dir,
    normalize_stream_url,
    preview_cache_path,
)
from backend.modules.stream.adapters.legacy_api import (
    aggregated_channels,
    get_instance_by_id,
    get_stream_capture_options,
)
from backend.modules.stream.core.pipeline import Pipeline
from backend.modules.stream.core.types import StreamResult, StreamTask

_log = logging.getLogger("nms.stream.playback")


def router_factory() -> APIRouter:
    router = APIRouter()
    _HEAVY_PREVIEW_SEMAPHORE, _ = get_heavy_semaphores()
    _pipeline = Pipeline()

    async def _refresh_preview_to_cache(instance_id: int, name: str) -> None:
        try:
            data = await aggregated_channels()
            ch = next(
                (c for c in (data.get("channels") or []) if c.get("instance_id") == instance_id and c.get("name") == name),
                None,
            )
            if not ch:
                return
            outputs = ch.get("output") or []
            if not outputs:
                return
            pair = get_instance_by_id(instance_id)
            stream_host = pair[0].host if pair else None
            url = normalize_stream_url(outputs[0], stream_host)
            opts = get_stream_capture_options()
            async with _HEAVY_PREVIEW_SEMAPHORE:
                resp = await asyncio.to_thread(
                    capture_frame,
                    url,
                    timeout=opts.get("timeout_sec", 10),
                    quality=opts.get("jpeg_quality") or 90,
                )
                if not resp.get("success"):
                    return
                raw = resp.get("data")
                if not raw:
                    return
            cache_path = preview_cache_path(instance_id, name)
            get_preview_cache_dir().mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(raw)
        except Exception as exc:  # pragma: no cover
            _log.warning("preview refresh failed: %s", exc)

    @router.post("/api/channels/preview-refresh/start")
    async def preview_refresh_start():
        try:
            data = await aggregated_channels()
            channels = data.get("channels") or []
            tasks = []
            for ch in channels:
                iid = ch.get("instance_id")
                name = ch.get("name")
                if iid is None or not name:
                    continue
                tasks.append(asyncio.create_task(_refresh_preview_to_cache(iid, name)))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            return {"started": True, "count": len(tasks)}
        except Exception as exc:
            _log.error("preview_refresh_start error: %s", exc)
            raise HTTPException(500, detail="Failed to start preview refresh") from exc

    @router.get("/api/channels/preview-refresh/status")
    async def preview_refresh_status():
        return {"running": False, "done_at": None}

    @router.get("/api/channels/preview-refresh/stream")
    async def preview_refresh_stream():
        async def _event_stream():
            while True:
                yield ": keepalive\n\n"
                await asyncio.sleep(1.5)

        return StreamingResponse(
            _event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.get("/api/instances/{instance_id}/channels/preview")
    async def channel_preview(instance_id: int, name: str):
        cache_path = preview_cache_path(instance_id, name)
        if not cache_path.is_file():
            raise HTTPException(404, detail="Preview not cached")
        return StreamingResponse(
            cache_path.open("rb"),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=60"},
        )

    @router.post("/api/streams/playback")
    async def start_stream_playback(body: dict[str, Any]):
        backend_id = body.get("backend") or body.get("backend_id") or "auto"
        input_url = body.get("input_url") or body.get("url")
        output_format = body.get("output_format") or "http_ts"
        if not input_url:
            raise HTTPException(400, detail="input_url required")
        task = StreamTask(
            id=str(uuid.uuid4()),
            type="stream",
            source_url=input_url,
            input_protocol=input_url.split(":", 1)[0],
            output_format=output_format,
            config={"backend": backend_id, "options": body.get("options", {})},
            timeout_sec=int(body.get("timeout_sec") or 30),
        )
        try:
            result: StreamResult = await _pipeline.process(task)
            if not result.success:
                raise HTTPException(500, detail=result.error_message or "Playback failed")
            return {
                "success": True,
                "backend": result.backend_name,
                "output_path": result.output_path,
                "metrics": result.metrics,
            }
        except HTTPException:
            raise
        except Exception as exc:
            _log.error("playback error: %s", exc)
            raise HTTPException(500, detail="Playback failed") from exc

    @router.post("/api/streams/playback/live")
    async def start_stream_playback_live(body: dict[str, Any]):
        input_url = body.get("input_url") or body.get("url")
        if not input_url:
            raise HTTPException(400, detail="input_url required")
        if not input_url.startswith(("http://", "https://", "rtsp://", "rtmp://", "rtmps://", "udp://", "srt://")):
            raise HTTPException(400, detail="unsupported protocol for live http_ts")
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise HTTPException(500, detail="ffmpeg not installed")

        cmd = [
            ffmpeg,
            "-re",
            "-i",
            input_url,
            "-c",
            "copy",
            "-f",
            "mpegts",
            "-",
        ]

        async def _stream():
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                while True:
                    chunk = await proc.stdout.read(8192)  # type: ignore[arg-type]
                    if not chunk:
                        break
                    yield chunk
            except asyncio.CancelledError:
                proc.kill()
                raise
            finally:
                if proc.returncode is None:
                    proc.kill()
                try:
                    await proc.communicate()
                except Exception:
                    pass

        return StreamingResponse(
            _stream(),
            media_type="video/MP2T",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
