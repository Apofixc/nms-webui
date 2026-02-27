"""Модуль потоков и превью."""
import asyncio

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse

from backend.modules.stream.services import tasks as rq_tasks
from backend.modules.astra.services.aggregator import aggregated_channels
from backend.modules.stream.services.state import (
    client_ip,
    get_heavy_semaphores,
    get_playback_sessions,
    get_preview_cache_dir,
    get_preview_refresh_job_id,
    get_preview_refresh_state,
    get_queue,
    get_stream_capture,
    get_stream_settings,
    get_whep_connections,
    normalize_stream_url,
    optional_sem,
    per_ip_semaphore,
    preview_cache_path,
    set_preview_refresh_job_id,
    set_preview_refresh_state,
)
from backend.modules.stream import (
    StreamPlaybackSession,
    get_input_format,
    get_backend_for_link,
)
from backend.modules.stream.core.converter import UniversalStreamConverter
from backend.modules.stream.outputs.webrtc_output import (
    is_whep_available,
    whep_handle_offer,
    whep_close,
    whep_unavailable_message,
)
from backend.core.webui_settings import (
    get_stream_capture_options,
    get_stream_playback_udp_backend,
    get_stream_playback_udp_backend_options,
    get_stream_playback_udp_output_format,
)
from backend.core.config import get_settings, get_instance_by_id
from backend.modules.stream.process_manager import get_stream_process_manager


def router_factory() -> APIRouter:
    router = APIRouter()
    process_manager = get_stream_process_manager()

    _HEAVY_PREVIEW_SEMAPHORE, _HEAVY_PLAYBACK_SEMAPHORE = get_heavy_semaphores()

    async def _refresh_preview_to_cache(instance_id: int, name: str) -> None:
        capture = get_stream_capture()
        if capture is None or not capture.available:
            return
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
            async with optional_sem(_HEAVY_PREVIEW_SEMAPHORE):
                raw = await asyncio.to_thread(
                    capture.capture,
                    url,
                    timeout_sec=opts.get("timeout_sec", 10.0),
                    output_format="jpeg",
                    jpeg_quality=opts.get("jpeg_quality"),
                )
            cache_path = preview_cache_path(instance_id, name)
            get_preview_cache_dir().mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(raw)
        except Exception:
            pass

    async def _run_full_preview_refresh() -> None:
        import time
        try:
            data = await aggregated_channels()
            channels = data.get("channels") or []
            with_output = [(c.get("instance_id"), c.get("name")) for c in channels if (c.get("output") or [])]
            for instance_id, name in with_output:
                if instance_id is None or not name:
                    continue
                await _refresh_preview_to_cache(instance_id, name)
        except Exception:
            pass
        finally:
            set_preview_refresh_state(False, time.time())

    def _build_preview_refresh_items(data: dict) -> list[dict]:
        channels = data.get("channels") or []
        items = []
        for c in channels:
            if not (c.get("output") or []):
                continue
            instance_id = c.get("instance_id")
            name = c.get("name")
            if instance_id is None or not name:
                continue
            pair = get_instance_by_id(instance_id)
            stream_host = pair[0].host if pair else None
            url = normalize_stream_url((c.get("output") or [])[0], stream_host)
            cache_path = preview_cache_path(instance_id, name)
            items.append({"url": url, "cache_path": str(cache_path.resolve())})
        return items

    @router.post("/api/channels/preview-refresh/start")
    async def channels_preview_refresh_start():
        import time
        cooldown = get_settings().preview_refresh_cooldown_sec
        running, done_at = get_preview_refresh_state()
        if running:
            return {"started": False, "reason": "already_running"}
        if done_at is not None and (time.time() - done_at) < cooldown:
            return {"started": False, "reason": "cooldown"}
        queue = get_queue()
        if queue is not None:
            try:
                data = await aggregated_channels()
                items = _build_preview_refresh_items(data)
                if not items:
                    return {"started": False, "reason": "no_channels"}
                job = queue.enqueue(rq_tasks.refresh_previews, items)
                set_preview_refresh_job_id(job.id)
                set_preview_refresh_state(True)
                return {"started": True, "job_id": job.id}
            except Exception as e:
                return {"started": False, "reason": "queue_error", "detail": str(e)}
        capture = get_stream_capture()
        if capture is None or not capture.available:
            return {"started": False, "reason": "capture_unavailable"}
        set_preview_refresh_state(True)
        asyncio.create_task(_run_full_preview_refresh())
        return {"started": True}

    def _sync_preview_refresh_from_job() -> None:
        job_id = get_preview_refresh_job_id()
        queue = get_queue()
        if not job_id or queue is None:
            return
        try:
            from rq.job import Job
            import time
            job = Job.fetch(job_id, connection=queue.connection)
            if job.is_finished or job.is_failed:
                set_preview_refresh_job_id(None)
                set_preview_refresh_state(False, job.ended_at.timestamp() if job.ended_at else time.time())
        except Exception:
            pass

    @router.get("/api/channels/preview-refresh/status")
    async def channels_preview_refresh_status():
        from datetime import datetime, timezone
        _sync_preview_refresh_from_job()
        running, done_at = get_preview_refresh_state()
        done_at_iso = None
        if done_at is not None:
            done_at_iso = datetime.fromtimestamp(done_at, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"running": running, "done_at": done_at_iso}

    @router.get("/api/channels/preview-refresh/stream")
    async def channels_preview_refresh_stream():
        from datetime import datetime, timezone

        async def event_stream():
            while True:
                _sync_preview_refresh_from_job()
                running, done_at = get_preview_refresh_state()
                if not running and done_at is not None:
                    done_at_iso = datetime.fromtimestamp(done_at, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    yield f"event: refresh_done\ndata: {{\"done_at\":\"{done_at_iso}\"}}\n\n"
                    return
                yield ": keepalive\n\n"
                await asyncio.sleep(1.5)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.get("/api/instances/{instance_id}/channels/preview")
    async def channel_preview(instance_id: int, name: str):
        from datetime import datetime, timezone
        data = await aggregated_channels()
        ch = next(
            (c for c in (data.get("channels") or []) if c.get("instance_id") == instance_id and c.get("name") == name),
            None,
        )
        if not ch:
            raise HTTPException(404, detail="Channel not found")
        if not (ch.get("output") or []):
            raise HTTPException(404, detail="Channel has no output URL")
        cache_path = preview_cache_path(instance_id, name)
        if not cache_path.exists():
            raise HTTPException(404, detail="Preview not in cache yet")
        mtime = cache_path.stat().st_mtime
        headers = {"X-Preview-Generated-At": datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        return FileResponse(cache_path, media_type="image/jpeg", headers=headers)

    @router.get("/api/streams/processes")
    async def streams_processes_status():
        return process_manager.status()

    @router.post("/api/streams/playback")
    async def start_stream_playback(request: Request, body: dict):
        try:
            url = body.get("url")
            stream_host = None
            if not url:
                instance_id = body.get("instance_id")
                channel_name = body.get("channel_name")
                if instance_id is None or not channel_name:
                    raise HTTPException(400, detail="Provide 'url' or 'instance_id' and 'channel_name'")
                data = await aggregated_channels()
                ch = next(
                    (c for c in (data.get("channels") or []) if c.get("instance_id") == instance_id and c.get("name") == channel_name),
                    None,
                )
                if not ch:
                    raise HTTPException(404, detail="Channel not found")
                outputs = ch.get("output") or []
                if not outputs:
                    raise HTTPException(404, detail="Channel has no output URL")
                url = outputs[0]
                pair = get_instance_by_id(instance_id)
                if pair:
                    stream_host = pair[0].host
            url = normalize_stream_url(url, stream_host)
            input_format = get_input_format(url)
            if not input_format:
                raise HTTPException(400, detail="Unsupported URL scheme")
            out_fmt = get_stream_playback_udp_output_format()
            output_for_registry = "http_hls" if out_fmt == "hls" else ("webrtc" if out_fmt == "webrtc" else "http_ts")
            opts = get_stream_playback_udp_backend_options()
            pref = get_stream_playback_udp_backend()
            try:
                backend_name = get_backend_for_link(pref, input_format, output_for_registry, opts)
            except ValueError as e:
                raise HTTPException(502, detail=str(e))
            per_ip = await per_ip_semaphore("playback", client_ip(request), get_settings().heavy_playback_per_ip)
            async with per_ip, optional_sem(_HEAVY_PLAYBACK_SEMAPHORE):
                session = StreamPlaybackSession()
                playback_url = session.start(
                    url,
                    output_format=out_fmt,
                    input_format=input_format,
                    backend_name=backend_name,
                    backend_options=opts,
                )
                sid = session._session_id
                if sid:
                    get_playback_sessions()[sid] = session
                    process_manager.register(
                        sid,
                        source_url=session.get_source_url(),
                        backend=backend_name,
                        output_format=out_fmt,
                    )
                if out_fmt == "webrtc":
                    playback_url = f"/api/streams/whep/{sid}"
            settings = get_stream_settings()["settings"]
            pb = settings.get("modules", {}).get("stream", {}).get("playback_udp", {})
            show_backend_and_format = pb.get("show_backend_and_format", True)
            return {
                "playback_url": playback_url,
                "session_id": sid,
                "playback_type": session.get_playback_type(),
                "use_mpegts_js": session.get_use_mpegts_js(),
                "use_native_video": session.get_use_native_video(),
                "backend": backend_name,
                "output_format": out_fmt,
                "show_backend_and_format": show_backend_and_format,
            }
        except HTTPException:
            raise
        except Exception as e:
            sid = locals().get("sid")
            if sid:
                process_manager.mark_failed(sid, str(e))
            raise HTTPException(502, detail=str(e))

    @router.get("/api/streams/live/{session_id}")
    async def stream_live_udp(session_id: str, request: Request):
        session = get_playback_sessions().get(session_id)
        if not session:
            raise HTTPException(404, detail="Session not found")
        opts = get_stream_playback_udp_backend_options()
        out_pref = get_stream_playback_udp_output_format()
        desired_output = "http_hls" if out_pref == "hls" else ("webrtc" if out_pref == "webrtc" else "http_ts")

        if desired_output == "webrtc":
            return RedirectResponse(
                url=f"/api/streams/whep/{session_id}",
                status_code=302,
                headers={"Cache-Control": "no-cache"},
            )

        if getattr(session, "_http_ts_to_hls", False):
            if session.get_session_dir() is not None:
                return RedirectResponse(
                    url=f"/api/streams/{session_id}/playlist.m3u8",
                    status_code=302,
                    headers={"Cache-Control": "no-cache"},
                )
            http_url = session.get_http_url()
            if not http_url:
                raise HTTPException(404, detail="No HTTP URL for session")
            backend_name = session.get_backend_name() or get_backend_for_link(
                get_stream_playback_udp_backend(), "http", "http_hls", opts
            )
            session_dir = session._output_base / session_id
            try:
                process = await UniversalStreamConverter.start_hls_async(
                    http_url, session_dir, backend_name, opts
                )
            except NotImplementedError as e:
                raise HTTPException(502, detail=str(e))
            except Exception as e:
                raise HTTPException(502, detail=f"Запуск {backend_name} HTTP→HLS: {e}")
            session.set_live_hls(session_dir, process)
            try:
                for _ in range(25):
                    if (session_dir / "playlist.m3u8").exists():
                        if (session_dir / "seg_000.ts").exists() or list(session_dir.glob("seg_*.ts")):
                            break
                    await asyncio.sleep(0.2)
                else:
                    raise HTTPException(502, detail="HLS playlist did not appear")
            except Exception:
                session.stop()
                raise
            return RedirectResponse(
                url=f"/api/streams/{session_id}/playlist.m3u8",
                status_code=302,
                headers={"Cache-Control": "no-cache"},
            )

        stream_url = session.get_udp_url() or session.get_source_url()
        if not stream_url:
            raise HTTPException(404, detail="No stream URL for session")
        backend_name = session.get_backend_name()
        if not backend_name:
            pref = get_stream_playback_udp_backend()
            try:
                backend_name = get_backend_for_link(
                    pref, session.get_input_format() or "udp", desired_output, opts
                )
            except ValueError as e:
                raise HTTPException(502, detail=str(e))
        opts = session.get_backend_options() or opts

        if desired_output == "http_hls":
            if session.get_session_dir() is not None:
                return RedirectResponse(
                    url=f"/api/streams/{session_id}/playlist.m3u8",
                    status_code=302,
                    headers={"Cache-Control": "no-cache"},
                )
            session_dir = session._output_base / session_id
            try:
                process = await UniversalStreamConverter.start_hls_async(
                    stream_url, session_dir, backend_name, opts
                )
            except NotImplementedError as e:
                raise HTTPException(502, detail=str(e))
            except Exception as e:
                raise HTTPException(502, detail=f"Запуск {backend_name} HLS: {e}")
            session.set_live_hls(session_dir, process)
            session_dir = session_dir.resolve()
            try:
                for _ in range(50):
                    pl = session_dir / "playlist.m3u8"
                    if pl.exists() and pl.stat().st_size > 0:
                        if list(session_dir.glob("seg_*.ts")) or list(session_dir.glob("seg-*.ts")) or list(session_dir.glob("segment*.ts")):
                            break
                    await asyncio.sleep(0.25)
                else:
                    raise HTTPException(502, detail="HLS playlist did not appear")
            except Exception:
                session.stop()
                raise
            return RedirectResponse(
                url=f"/api/streams/{session_id}/playlist.m3u8",
                status_code=302,
                headers={"Cache-Control": "no-cache"},
            )

        try:
            return StreamingResponse(
                UniversalStreamConverter.stream(stream_url, request, backend_name, opts),
                media_type="video/mp2t",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        except NotImplementedError:
            raise HTTPException(502, detail=f"Бэкенд «{backend_name}» не реализовал stream()")

    @router.get("/api/streams/proxy/{session_id}/{path:path}")
    async def stream_proxy(session_id: str, path: str):
        session = get_playback_sessions().get(session_id)
        if not session:
            raise HTTPException(404, detail="Session not found")
        base = session.get_http_base_url()
        if not base:
            raise HTTPException(404, detail="Not an HTTP session")
        import httpx
        path_clean = (path or "").strip().lstrip("/")
        if not path_clean:
            url = session.get_http_url()
        else:
            url = base.rstrip("/") + "/" + path_clean
        if not url:
            raise HTTPException(404, detail="No URL")
        is_live_ts = not path_clean and not url.rstrip("/").lower().endswith(".m3u8")
        media_type = "application/vnd.apple.mpegurl" if (path_clean.endswith(".m3u8") or (not path_clean and ".m3u8" in url.lower())) else "video/mp2t"
        headers = {
            "User-Agent": "NMS-WebUI-Proxy/1.0",
            "Accept": "video/mp2t,video/*,*/*;q=0.8" if is_live_ts else "application/vnd.apple.mpegurl,video/*,*/*;q=0.8",
        }
        stream_timeout = httpx.Timeout(30.0, read=3600.0) if is_live_ts else 30.0
        try:
            if is_live_ts:
                client = httpx.AsyncClient(timeout=stream_timeout, follow_redirects=True)
                stream_ctx = client.stream("GET", url, headers=headers)
                r = await stream_ctx.__aenter__()
                try:
                    r.raise_for_status()
                except Exception:
                    await stream_ctx.__aexit__(None, None, None)
                    await client.aclose()
                    raise
                stream_iter = r.aiter_bytes(chunk_size=32768)
                first_chunk = None
                try:
                    first_chunk = await stream_iter.__anext__()
                except (StopAsyncIteration, httpx.ReadError, httpx.RemoteProtocolError, httpx.StreamClosed, OSError):
                    pass
                if not first_chunk:
                    await stream_ctx.__aexit__(None, None, None)
                    await client.aclose()
                    raise HTTPException(
                        502,
                        detail="Поток не отдаёт данные. Проверьте, что URL доступен с сервера (curl с хоста бэкенда).",
                    )

                async def chunk_gen():
                    try:
                        yield first_chunk
                        try:
                            async for chunk in stream_iter:
                                yield chunk
                        except (httpx.ReadError, httpx.RemoteProtocolError, httpx.StreamClosed, OSError):
                            pass
                    finally:
                        await stream_ctx.__aexit__(None, None, None)
                        await client.aclose()

                resp = StreamingResponse(chunk_gen(), media_type=media_type)
                resp.headers["Cache-Control"] = "no-cache, no-store"
                resp.headers["X-Accel-Buffering"] = "no"
                resp.headers["Accept-Ranges"] = "none"
                return resp
            async with httpx.AsyncClient(timeout=stream_timeout, follow_redirects=True) as client:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                return Response(content=r.content, media_type=media_type)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(502, detail=str(e))

    @router.get("/api/streams/{session_id}/{path:path}")
    async def stream_session_file(session_id: str, path: str):
        session = get_playback_sessions().get(session_id)
        if not session:
            raise HTTPException(404, detail="Session not found")
        session_dir = session.get_session_dir()
        if not session_dir:
            raise HTTPException(404, detail="Session dir not found")
        file_path = session_dir / path
        try:
            if not file_path.resolve().is_relative_to(session_dir.resolve()):
                raise HTTPException(403, detail="Invalid path")
        except ValueError:
            raise HTTPException(403, detail="Invalid path")
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(404, detail=f"File not found: {path} (session alive: {session.is_alive()})")
        media_type = "application/vnd.apple.mpegurl" if path.endswith(".m3u8") else "video/mp2t"
        return FileResponse(file_path, media_type=media_type)

    @router.post("/api/streams/whep/{session_id}")
    async def whep_post(session_id: str, request: Request):
        connections = get_whep_connections()
        session = get_playback_sessions().get(session_id)
        if not session:
            raise HTTPException(404, detail="Session not found")
        if session.get_playback_type() != "webrtc":
            raise HTTPException(400, detail="Session is not a WebRTC session")
        if not is_whep_available():
            raise HTTPException(503, detail=whep_unavailable_message())
        stream_url = session.get_udp_url() or session.get_source_url()
        body = await request.body()
        sdp_offer = body.decode("utf-8", errors="replace").strip()
        if not sdp_offer:
            raise HTTPException(400, detail="SDP offer required")
        try:
            sdp_answer, pc, player = await whep_handle_offer(sdp_offer, source_url=stream_url)
        except RuntimeError as e:
            raise HTTPException(503, detail=str(e))
        except Exception as e:
            raise HTTPException(502, detail=f"WHEP offer failed: {e}")
        connections[session_id] = (pc, player)
        location = f"/api/streams/whep/{session_id}"
        return Response(
            content=sdp_answer,
            status_code=201,
            media_type="application/sdp",
            headers={"Location": location, "Cache-Control": "no-cache"},
        )

    @router.delete("/api/streams/whep/{session_id}")
    async def whep_delete(session_id: str):
        connections = get_whep_connections()
        conn = connections.pop(session_id, None)
        if conn is not None:
            pc, player = conn if isinstance(conn, tuple) and len(conn) >= 2 else (conn, None)
            await whep_close(pc, player)
        return Response(status_code=204)

    @router.delete("/api/streams/playback/{session_id}")
    async def stop_stream_playback(session_id: str):
        connections = get_whep_connections()
        session = get_playback_sessions().pop(session_id, None)
        if not session:
            raise HTTPException(404, detail="Session not found")
        session.stop()
        process_manager.unregister(session_id)
        conn = connections.pop(session_id, None)
        if conn is not None:
            pc, player = conn if isinstance(conn, tuple) and len(conn) >= 2 else (conn, None)
            await whep_close(pc, player)
        return {"message": "stopped"}

    return router
