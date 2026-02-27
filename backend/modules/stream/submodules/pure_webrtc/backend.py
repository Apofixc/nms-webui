from __future__ import annotations

import json
import uuid
import time
from typing import Any

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import StreamResult, StreamTask


try:  # optional dependency
    from aiortc import RTCPeerConnection, RTCSessionDescription

    _AIORTC_AVAILABLE = True
except Exception:  # pragma: no cover - aiortc не установлен
    _AIORTC_AVAILABLE = False


class SimplePeerState:
    """Простое состояние peer connection для инспекции."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.local_offer: str | None = None
        self.local_answer: str | None = None
        self.ice_gathering_complete = False
        self.connection_state = "new"
        self.signaling_state = "stable"
        self.created_at = time.time()

    def set_offer(self, sdp: str) -> None:
        self.local_offer = sdp
        self.signaling_state = "have-local-offer"

    def set_answer(self, sdp: str) -> None:
        self.local_answer = sdp
        self.signaling_state = "stable"
        self.connection_state = "connected"
        self.ice_gathering_complete = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "local_offer": self.local_offer,
            "local_answer": self.local_answer,
            "ice_gathering_complete": self.ice_gathering_complete,
            "connection_state": self.connection_state,
            "signaling_state": self.signaling_state,
            "created_at": self.created_at,
        }


class PureWebRTCBackend(IStreamBackend):
    """WebRTC signalling субмодуль. Использует aiortc, если доступен; иначе возвращает ошибку."""

    def __init__(self):
        self._available = _AIORTC_AVAILABLE
        self._sessions: dict[str, SimplePeerState] = {}

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "protocols": ["http", "webrtc", "rtsp"],
            "outputs": ["webrtc"],
            "features": ["python_only", "webrtc", "signaling"],
            "priority_matrix": {
                "http": {"webrtc": 60},
                "rtsp": {"webrtc": 60},
            },
        }

    def match_score(self, input_proto: str, output_format: str) -> int:
        caps = self.get_capabilities()
        if input_proto in caps.get("protocols", []) and output_format in caps.get("outputs", []):
            return int((caps.get("priority_matrix", {}).get(input_proto, {}) or {}).get(output_format, 20))
        return 0

    async def initialize(self, config: dict[str, Any]) -> bool:
        self._available = _AIORTC_AVAILABLE
        return self._available

    async def health_check(self) -> bool:
        return self._available

    async def shutdown(self) -> None:
        self._sessions.clear()

    async def process(self, task: StreamTask) -> StreamResult:
        if not self._available:
            return StreamResult(success=False, output_path=None, backend_name="pure_webrtc", error="aiortc not installed")

        session_id = task.id or str(uuid.uuid4())
        state = SimplePeerState(session_id)

        pc = RTCPeerConnection()
        # создаём datachannel, чтобы форсировать ICE/SDP
        pc.createDataChannel("noop")

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        # Ждём, пока ICE кандидаты соберутся в localDescription (короткая задержка)
        await asyncio.sleep(0.1)

        # Для демонстрации создаём локальный answer (без удалённого SDP)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        state.set_offer(pc.localDescription.sdp if pc.localDescription else "")
        state.set_answer(answer.sdp if answer else "")
        self._sessions[session_id] = state

        payload = {
            "session_id": session_id,
            "offer": {"type": "offer", "sdp": state.local_offer},
            "answer": {"type": "answer", "sdp": state.local_answer},
            "state": state.to_dict(),
        }
        return StreamResult(success=True, output_path=json.dumps(payload), backend_name="pure_webrtc")
