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
        
        # Для асинхронного получения Offer
        self._offer_ready = asyncio.Event()
        self._error = None
        self._init_task = None

    def initialize(self):
        """Запуск фоновой инициализации."""
        self._running = True
        self._init_task = asyncio.create_task(self._run_init())
        return self._init_task

    async def _run_init(self):
        """Внутренний метод инициализации (выполняется в фоне)."""
        try:
            from aiortc import RTCPeerConnection, RTCConfiguration, RTCIceServer
            from aiortc.contrib.media import MediaPlayer

            logger.info(f"WebRTC {self.task_id}: starting initialization for {self.input_url}")

            # ICE-серверы
            ice_servers = []
            stun = self.settings.get("pure_webrtc_stun_server") or self.settings.get("stun_server", "stun:stun.l.google.com:19302")
            if stun:
                ice_servers.append(RTCIceServer(urls=[stun]))
            turn = self.settings.get("pure_webrtc_turn_server") or self.settings.get("turn_server", "")
            if turn:
                ice_servers.append(RTCIceServer(urls=[turn]))

            config = RTCConfiguration(iceServers=ice_servers) if ice_servers else RTCConfiguration()
            self._pc = RTCPeerConnection(configuration=config)

            # MediaPlayer может инициализироваться долго (открытие потока)
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

            # Ждем сбора кандидатов (небольшой таймаут, чтобы не блокировать вечно)
            if self._pc.iceGatheringState != "complete":
                try:
                    gathering_complete = asyncio.Event()
                    @self._pc.on("icegatheringstatechange")
                    def on_icegatheringstatechange():
                        if self._pc.iceGatheringState == "complete":
                            gathering_complete.set()
                    
                    # Даем 2 секунды на сбор базовых кандидатов
                    await asyncio.wait_for(gathering_complete.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning(f"WebRTC {self.task_id}: ICE gathering timeout, continuing with partial candidates")
                except Exception as e:
                    logger.error(f"WebRTC {self.task_id}: ICE gathering error: {e}")

            # Сигнализируем о готовности
            logger.info(f"WebRTC {self.task_id}: Offer ready")
            self._offer_ready.set()

        except Exception as e:
            self._error = str(e)
            logger.error(f"WebRTC {self.task_id} init error: {e}")
            self._offer_ready.set() # Освобождаем ждущих, чтобы они увидели ошибку
            await self.stop()

    async def wait_for_offer(self, timeout: float = 20.0) -> dict:
        """Ожидание готовности Offer (Long Polling)."""
        try:
            await asyncio.wait_for(self._offer_ready.wait(), timeout=timeout)
            
            if self._error:
                raise RuntimeError(self._error)
                
            if not self._pc or not self._pc.localDescription:
                raise RuntimeError("Offer not generated")
                
            return {
                "sdp": self._pc.localDescription.sdp,
                "type": self._pc.localDescription.type,
            }
        except asyncio.TimeoutError:
            raise RuntimeError("Timed out waiting for WebRTC offer")

    async def set_remote_description(self, sdp: str, type: str = "answer"):
        """Установка удаленного описания (ответа от клиента)."""
        # Ждем завершения инициализации, если она еще идет
        if not self._offer_ready.is_set():
            await self.wait_for_offer()

        if not self._pc:
            raise RuntimeError("PeerConnection не инициализирован")
            
        from aiortc import RTCSessionDescription
        description = RTCSessionDescription(sdp=sdp, type=type)
        await self._pc.setRemoteDescription(description)
        logger.info(f"WebRTC {self.task_id}: remote description set ({type})")

    async def stop(self):
        self._running = False
        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
        if self._pc:
            await self._pc.close()
            self._pc = None
        if self._player:
            self._player = None 


class PureWebRTCStreamer:
    """Управление WebRTC сессиями."""

    def __init__(self, settings: dict):
        self.settings = settings
        self.video_codec = settings.get("pure_webrtc_video_codec", "H264")
        self.max_bitrate = settings.get("pure_webrtc_max_bitrate", 2000)
        self.ice_timeout = settings.get("pure_webrtc_ice_timeout", 30)
        self._sessions: Dict[str, WebRTCSession] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        """Мгновенный запуск сессии (инициализация в фоне)."""
        # Используем task_id из воркер-пула (важно для роутинга signaling)
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            session = WebRTCSession(
                task_id=task_id,
                input_url=task.input_url,
                settings=self.settings
            )
            self._sessions[task_id] = session
            
            # Запускаем инициализацию в фоне
            session.initialize()

            # Возвращаем результат немедленно
            return StreamResult(
                task_id=task_id, success=True, backend_used="pure_webrtc",
                output_type=OutputType.WEBRTC,
                output_url=f"/api/modules/stream/v1/webrtc/{task_id}",
                metadata={
                    "status": "initializing",
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

