# Субмодуль Pure WebRTC — нативный низкозадержковый стриминг
# Использует aiortc для WebRTC peer connection
import asyncio
import logging
import uuid
from typing import Dict, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

logger = logging.getLogger(__name__)


class WebRTCSession:
    """Активная WebRTC сессия."""

    def __init__(self, task_id: str, input_url: str) -> None:
        self.task_id = task_id
        self.input_url = input_url
        self._pc = None  # RTCPeerConnection
        self._running = False

    async def start(self) -> dict:
        """Инициализация WebRTC peer connection.

        Возвращает SDP offer для клиента.
        """
        try:
            from aiortc import RTCPeerConnection, RTCSessionDescription
            from aiortc.contrib.media import MediaPlayer

            self._pc = RTCPeerConnection()
            self._running = True

            # Создание медиа-плеера из входного URL
            player = MediaPlayer(self.input_url)

            # Добавление треков
            if player.audio:
                self._pc.addTrack(player.audio)
            if player.video:
                self._pc.addTrack(player.video)

            # Обработка события закрытия соединения
            @self._pc.on("connectionstatechange")
            async def on_state_change():
                state = self._pc.connectionState
                logger.info(f"WebRTC [{self.task_id}] состояние: {state}")
                if state in ("failed", "closed"):
                    self._running = False

            # Создание SDP offer
            offer = await self._pc.createOffer()
            await self._pc.setLocalDescription(offer)

            return {
                "sdp": self._pc.localDescription.sdp,
                "type": self._pc.localDescription.type,
            }

        except ImportError:
            raise RuntimeError("aiortc не установлен. Установите: pip install aiortc")
        except Exception as e:
            raise RuntimeError(f"Ошибка инициализации WebRTC: {e}")

    async def set_answer(self, sdp: str, sdp_type: str = "answer") -> None:
        """Установка SDP answer от клиента."""
        try:
            from aiortc import RTCSessionDescription
            answer = RTCSessionDescription(sdp=sdp, type=sdp_type)
            await self._pc.setRemoteDescription(answer)
        except Exception as e:
            logger.error(f"WebRTC [{self.task_id}] ошибка установки answer: {e}")

    async def stop(self) -> None:
        """Закрытие WebRTC соединения."""
        self._running = False
        if self._pc:
            await self._pc.close()
            self._pc = None


class PureWebRTCBackend(IStreamBackend):
    """Нативный Python-бэкенд для WebRTC стриминга.

    Требует установки библиотеки aiortc:
        pip install aiortc

    Поддерживает входные протоколы HTTP, UDP, RTP.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, WebRTCSession] = {}
        self._aiortc_available: Optional[bool] = None

    @property
    def backend_id(self) -> str:
        return "pure_webrtc"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.UDP, StreamProtocol.RTP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.WEBRTC}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск WebRTC сессии."""
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            session = WebRTCSession(task_id=task_id, input_url=task.input_url)
            offer = await session.start()
            self._sessions[task_id] = session

            logger.info(f"WebRTC [{task_id}]: сессия создана для {task.input_url}")

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="pure_webrtc",
                output_url=f"/api/v1/m/stream/webrtc/{task_id}",
                metadata={
                    "sdp_offer": offer,
                    "protocol": task.input_protocol.value,
                },
            )
        except Exception as e:
            logger.error(f"WebRTC [{task_id}] ошибка: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id,
                success=False,
                backend_used="pure_webrtc",
                error=str(e),
            )

    async def stop_stream(self, task_id: str) -> bool:
        """Остановка WebRTC сессии."""
        session = self._sessions.pop(task_id, None)
        if session:
            await session.stop()
            logger.info(f"WebRTC [{task_id}] остановлен")
            return True
        return False

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return None

    async def is_available(self) -> bool:
        """Проверка наличия aiortc."""
        if self._aiortc_available is None:
            try:
                import aiortc  # noqa: F401
                self._aiortc_available = True
            except ImportError:
                self._aiortc_available = False
        return self._aiortc_available

    async def health_check(self) -> dict:
        available = await self.is_available()
        return {
            "backend": "pure_webrtc",
            "native": True,
            "aiortc_available": available,
            "active_sessions": len(self._sessions),
            "available": available,
        }

    def get_session(self, task_id: str) -> Optional[WebRTCSession]:
        """Получение сессии для SDP answer."""
        return self._sessions.get(task_id)


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Pure WebRTC."""
    return PureWebRTCBackend()
