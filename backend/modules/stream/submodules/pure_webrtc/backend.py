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

    def __init__(self, task_id: str, input_url: str, settings: dict):
        self.task_id = task_id
        self.input_url = input_url
        self.settings = settings
        self._pc = None
        self._running = False
        self._player = None

    async def start(self) -> dict:
        try:
            from aiortc import RTCPeerConnection, RTCConfiguration, RTCIceServer
            from aiortc.contrib.media import MediaPlayer

            # ICE-серверы (используем префикс pure_webrtc_)
            ice_servers = []
            stun = self.settings.get("pure_webrtc_stun_server") or self.settings.get("stun_server", "stun:stun.l.google.com:19302")
            if stun:
                ice_servers.append(RTCIceServer(urls=[stun]))
            turn = self.settings.get("pure_webrtc_turn_server") or self.settings.get("turn_server", "")
            if turn:
                ice_servers.append(RTCIceServer(urls=[turn]))

            config = RTCConfiguration(iceServers=ice_servers) if ice_servers else RTCConfiguration()
            self._pc = RTCPeerConnection(configuration=config)
            self._running = True

            # Возврат к стандартному MediaPlayer (без опций, которые ломали обнаружение дорожек)
            self._player = MediaPlayer(self.input_url)
            
            if self._player.audio:
                self._pc.addTrack(self._player.audio)
            if self._player.video:
                self._pc.addTrack(self._player.video)

            @self._pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"WebRTC {self.task_id} connection state: {self._pc.connectionState}")
                if self._pc.connectionState == "failed":
                    await self.stop()

            # Создаем Offer
            offer = await self._pc.createOffer()
            await self._pc.setLocalDescription(offer)

            # Ждем сбора кандидатов (базовый вариант)
            if self._pc.iceGatheringState != "complete":
                try:
                    gathering_complete = asyncio.Event()
                    @self._pc.on("icegatheringstatechange")
                    def on_icegatheringstatechange():
                        if self._pc.iceGatheringState == "complete":
                            gathering_complete.set()
                    await asyncio.wait_for(gathering_complete.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    pass

            return {
                "sdp": self._pc.localDescription.sdp,
                "type": self._pc.localDescription.type,
            }

        except ImportError:
            raise RuntimeError("aiortc не установлен")
        except Exception as e:
            logger.error(f"WebRTC start error: {e}")
            raise RuntimeError(f"Ошибка WebRTC: {e}")

    async def set_remote_description(self, sdp: str, type: str = "answer"):
        """Установка удаленного описания (ответа от клиента)."""
        if not self._pc:
            raise RuntimeError("PeerConnection не инициализирован")
            
        from aiortc import RTCSessionDescription
        description = RTCSessionDescription(sdp=sdp, type=type)
        await self._pc.setRemoteDescription(description)
        logger.info(f"WebRTC {self.task_id}: remote description set ({type})")

    async def stop(self):
        self._running = False
        if self._pc:
            await self._pc.close()
            self._pc = None
        if self._player:
            self._player = None 


class PureWebRTCStreamer:
    """Управление WebRTC сессиями.

    Настройки (STUN/TURN, кодек, битрейт) передаются через settings.
    """

    def __init__(self, settings: dict):
        self.settings = settings

        self.video_codec = settings.get("pure_webrtc_video_codec", "H264")
        self.max_bitrate = settings.get("pure_webrtc_max_bitrate", 2000)
        self.ice_timeout = settings.get("pure_webrtc_ice_timeout", 30)

        self._sessions: Dict[str, WebRTCSession] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            session = WebRTCSession(
                task_id=task_id,
                input_url=task.input_url,
                settings=self.settings
            )
            offer = await session.start()
            self._sessions[task_id] = session

            return StreamResult(
                task_id=task_id, success=True, backend_used="pure_webrtc",
                output_url=f"/api/modules/stream/v1/webrtc/{task_id}",
                metadata={
                    "sdp_offer": offer,
                    "video_codec": self.video_codec,
                    "max_bitrate": self.max_bitrate,
                }
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

    def get_session(self, task_id: str) -> Optional[WebRTCSession]:
        """Получить активную сессию по ID."""
        return self._sessions.get(task_id)

    def get_active_count(self) -> int:
        return len(self._sessions)
