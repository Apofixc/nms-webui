# Нативная логика WebRTC на базе aiortc
import asyncio
import logging
import uuid
from typing import Dict, Optional

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

logger = logging.getLogger(__name__)


class WebRTCSession:
    """Активная WebRTC сессия."""

    def __init__(self, task_id: str, input_url: str):
        self.task_id = task_id
        self.input_url = input_url
        self._pc = None
        self._running = False

    async def start(self) -> dict:
        try:
            from aiortc import RTCPeerConnection, RTCSessionDescription
            from aiortc.contrib.media import MediaPlayer

            self._pc = RTCPeerConnection()
            self._running = True

            player = MediaPlayer(self.input_url)
            if player.audio:
                self._pc.addTrack(player.audio)
            if player.video:
                self._pc.addTrack(player.video)

            offer = await self._pc.createOffer()
            await self._pc.setLocalDescription(offer)

            return {
                "sdp": self._pc.localDescription.sdp,
                "type": self._pc.localDescription.type,
            }

        except ImportError:
            raise RuntimeError("aiortc не установлен")
        except Exception as e:
            raise RuntimeError(f"Ошибка WebRTC: {e}")

    async def stop(self):
        self._running = False
        if self._pc:
            await self._pc.close()
            self._pc = None


class PureWebRTCStreamer:
    """Управление WebRTC сессиями."""

    def __init__(self):
        self._sessions: Dict[str, WebRTCSession] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            session = WebRTCSession(task_id=task_id, input_url=task.input_url)
            offer = await session.start()
            self._sessions[task_id] = session

            return StreamResult(
                task_id=task_id, success=True, backend_used="pure_webrtc",
                output_url=f"/api/v1/m/stream/webrtc/{task_id}",
                metadata={"sdp_offer": offer}
            )
        except Exception as e:
            logger.error(f"WebRTC ошибка [{task_id}]: {e}")
            return StreamResult(
                task_id=task_id, success=False, backend_used="pure_webrtc", error=str(e)
            )

    async def stop(self, task_id: str) -> bool:
        session = self._sessions.pop(task_id, None)
        if session:
            await session.stop()
            return True
        return False

    def get_active_count(self) -> int:
        return len(self._sessions)
