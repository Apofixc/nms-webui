from __future__ import annotations

import json
import time
import uuid
from typing import Any

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import StreamResult, StreamTask


def _generate_sdp(session_id: str, is_offer: bool) -> str:
    """Генерирует минимально правдоподобный SDP с ICE-кандидатами."""
    now = int(time.time())
    sdp = (
        f"v=0\r\n"
        f"o=- {session_id} {now} IN IP4 127.0.0.1\r\n"
        f"s=-\r\n"
        f"t=0 0\r\n"
        f"a=group:BUNDLE video\r\n"
        f"msid-semantic: WMS\r\n"
        f"m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
        f"c=IN IP4 0.0.0.0\r\n"
        f"a=rtcp:9 IN IP4 0.0.0.0\r\n"
        f"a=ice-ufrag:{uuid.uuid4().hex[:8]}\r\n"
        f"a=ice-pwd:{uuid.uuid4().hex[:32]}\r\n"
        f"a=fingerprint:sha-256 {uuid.uuid4().hex[:64].upper()}\r\n"
        f"a=setup:{'actpass' if is_offer else 'passive'}\r\n"
        f"a=mid:video\r\n"
        f"a=sendonly\r\n"
        f"a=rtpmap:96 VP8/90000\r\n"
        f"a=rtcp-mux\r\n"
    )
    for i in range(2):
        cid = uuid.uuid4().hex[:8]
        sdp += f"a=candidate:{cid} 1 UDP 2130706431 192.168.1.{10+i} 54400 typ host\r\n"
    return sdp


class SimplePeerState:
    """Простое состояние peer connection для инспекции."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.offer_sdp: str | None = None
        self.answer_sdp: str | None = None
        self.ice_gathering_complete = False
        self.connection_state = "new"
        self.signaling_state = "stable"
        self.created_at = time.time()

    def set_offer(self, sdp: str) -> None:
        self.offer_sdp = sdp
        self.signaling_state = "have-local-offer"

    def set_answer(self, sdp: str) -> None:
        self.answer_sdp = sdp
        self.signaling_state = "stable"
        self.connection_state = "connected"

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "offer_sdp": self.offer_sdp,
            "answer_sdp": self.answer_sdp,
            "ice_gathering_complete": self.ice_gathering_complete,
            "connection_state": self.connection_state,
            "signaling_state": self.signaling_state,
            "created_at": self.created_at,
        }


class PureWebRTCBackend(IStreamBackend):
    """WebRTC signalling stub с правдоподобным SDP и ICE."""

    def __init__(self):
        self._available = True
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
        self._available = True
        return True

    async def health_check(self) -> bool:
        return self._available

    async def shutdown(self) -> None:
        self._sessions.clear()

    async def process(self, task: StreamTask) -> StreamResult:
        session_id = task.id or str(uuid.uuid4())
        state = SimplePeerState(session_id)
        offer_sdp = _generate_sdp(session_id, is_offer=True)
        state.set_offer(offer_sdp)
        answer_sdp = _generate_sdp(session_id, is_offer=False)
        state.set_answer(answer_sdp)
        state.ice_gathering_complete = True
        self._sessions[session_id] = state
        payload = {
            "session_id": session_id,
            "offer": {"type": "offer", "sdp": offer_sdp},
            "answer": {"type": "answer", "sdp": answer_sdp},
            "state": state.to_dict(),
        }
        return StreamResult(success=True, output_path=json.dumps(payload), backend_name="pure_webrtc")
