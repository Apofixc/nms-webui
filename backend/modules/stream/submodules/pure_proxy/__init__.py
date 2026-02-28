# Субмодуль Pure Proxy — нативное проксирование без внешних бинарников
# HTTP/HLS Bypass + UDP-to-HTTP конвертация
import asyncio
import logging
import socket
import struct
import uuid
from typing import Dict, Optional, Set

import aiohttp

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

logger = logging.getLogger(__name__)


class ProxySession:
    """Активная проксирующая сессия."""

    def __init__(
        self,
        task_id: str,
        input_url: str,
        protocol: StreamProtocol,
    ) -> None:
        self.task_id = task_id
        self.input_url = input_url
        self.protocol = protocol
        self._running = False
        self._task: Optional[asyncio.Task] = None
        # Буфер для клиентов, подключённых к выходу
        self._buffer: asyncio.Queue[bytes] = asyncio.Queue(maxsize=256)
        self._udp_transport: Optional[asyncio.DatagramTransport] = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Запуск проксирующей сессии в зависимости от протокола."""
        self._running = True
        if self.protocol == StreamProtocol.UDP:
            self._task = asyncio.create_task(self._proxy_udp())
        elif self.protocol == StreamProtocol.HLS:
            self._task = asyncio.create_task(self._proxy_hls())
        else:
            self._task = asyncio.create_task(self._proxy_http())

    async def stop(self) -> None:
        """Остановка сессии."""
        self._running = False
        if self._udp_transport:
            self._udp_transport.close()
            self._udp_transport = None
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def read_chunk(self, timeout: float = 5.0) -> Optional[bytes]:
        """Чтение одного чанка из буфера."""
        try:
            return await asyncio.wait_for(self._buffer.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    # --- HTTP Proxy ---

    async def _proxy_http(self) -> None:
        """Проксирование HTTP потока (MPEG-TS) в буфер."""
        logger.info(f"[{self.task_id}] HTTP proxy: {self.input_url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.input_url,
                    timeout=aiohttp.ClientTimeout(total=None, sock_read=30),
                ) as resp:
                    if resp.status != 200:
                        logger.error(
                            f"[{self.task_id}] HTTP proxy: статус {resp.status}"
                        )
                        return

                    async for chunk in resp.content.iter_chunked(65536):
                        if not self._running:
                            break
                        try:
                            self._buffer.put_nowait(chunk)
                        except asyncio.QueueFull:
                            # Сбрасываем старые данные при переполнении
                            try:
                                self._buffer.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
                            self._buffer.put_nowait(chunk)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[{self.task_id}] HTTP proxy ошибка: {e}")
        finally:
            self._running = False

    # --- HLS Proxy ---

    async def _proxy_hls(self) -> None:
        """Проксирование HLS потока: скачивание сегментов по плейлисту."""
        logger.info(f"[{self.task_id}] HLS proxy: {self.input_url}")
        seen_segments: set = set()

        try:
            async with aiohttp.ClientSession() as session:
                while self._running:
                    # Загрузка плейлиста
                    async with session.get(self.input_url) as resp:
                        if resp.status != 200:
                            await asyncio.sleep(1)
                            continue
                        playlist_text = await resp.text()

                    # Парсинг сегментов из M3U8
                    segments = self._parse_m3u8_segments(playlist_text)
                    base_url = self.input_url.rsplit("/", 1)[0]

                    for seg_url in segments:
                        if seg_url in seen_segments or not self._running:
                            continue
                        seen_segments.add(seg_url)

                        # Абсолютный URL
                        if not seg_url.startswith("http"):
                            seg_url = f"{base_url}/{seg_url}"

                        # Загрузка сегмента
                        try:
                            async with session.get(seg_url) as seg_resp:
                                if seg_resp.status == 200:
                                    data = await seg_resp.read()
                                    try:
                                        self._buffer.put_nowait(data)
                                    except asyncio.QueueFull:
                                        try:
                                            self._buffer.get_nowait()
                                        except asyncio.QueueEmpty:
                                            pass
                                        self._buffer.put_nowait(data)
                        except Exception as e:
                            logger.warning(
                                f"[{self.task_id}] HLS сегмент ошибка {seg_url}: {e}"
                            )

                    # Ожидание обновления плейлиста
                    await asyncio.sleep(2)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[{self.task_id}] HLS proxy ошибка: {e}")
        finally:
            self._running = False

    def _parse_m3u8_segments(self, text: str) -> list[str]:
        """Простой парсер M3U8: извлекает URL сегментов."""
        segments = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                segments.append(line)
        return segments

    # --- UDP-to-HTTP ---

    async def _proxy_udp(self) -> None:
        """Конвертация UDP (multicast/unicast) в буфер для HTTP-выдачи.

        Поддерживает:
        - udp://<multicast_ip>:<port>  (multicast)
        - udp://<ip>:<port>            (unicast)
        - udp://:<port>                (любой на порт)
        """
        logger.info(f"[{self.task_id}] UDP proxy: {self.input_url}")

        # Парсинг UDP URL: udp://239.1.1.1:5500 или udp://@239.1.1.1:5500
        url = self.input_url.replace("udp://", "").replace("@", "")
        parts = url.split(":")
        if len(parts) != 2:
            logger.error(f"[{self.task_id}] Неверный UDP URL: {self.input_url}")
            return

        host = parts[0] or "0.0.0.0"
        try:
            port = int(parts[1])
        except ValueError:
            logger.error(f"[{self.task_id}] Неверный порт: {parts[1]}")
            return

        try:
            loop = asyncio.get_running_loop()

            # Определяем, multicast или unicast
            is_multicast = self._is_multicast(host)

            class UDPProtocol(asyncio.DatagramProtocol):
                """Приёмник UDP дейтаграмм."""

                def __init__(self, session: "ProxySession") -> None:
                    self._session = session

                def datagram_received(self, data: bytes, addr) -> None:
                    if not self._session._running:
                        return
                    try:
                        self._session._buffer.put_nowait(data)
                    except asyncio.QueueFull:
                        try:
                            self._session._buffer.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                        try:
                            self._session._buffer.put_nowait(data)
                        except asyncio.QueueFull:
                            pass

                def error_received(self, exc) -> None:
                    logger.warning(f"UDP ошибка: {exc}")

            # Создание UDP сокета
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Увеличиваем буфер приёма
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
            sock.bind(("0.0.0.0", port))

            if is_multicast:
                # Подписка на multicast группу
                mreq = struct.pack(
                    "4sl",
                    socket.inet_aton(host),
                    socket.INADDR_ANY,
                )
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                logger.info(f"[{self.task_id}] Multicast подписка: {host}:{port}")

            transport, _ = await loop.create_datagram_endpoint(
                lambda: UDPProtocol(self),
                sock=sock,
            )
            self._udp_transport = transport

            # Ожидание остановки
            while self._running:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[{self.task_id}] UDP proxy ошибка: {e}", exc_info=True)
        finally:
            if self._udp_transport:
                self._udp_transport.close()
            self._running = False

    @staticmethod
    def _is_multicast(ip: str) -> bool:
        """Проверка, является ли адрес multicast (224.0.0.0 – 239.255.255.255)."""
        try:
            parts = ip.split(".")
            return 224 <= int(parts[0]) <= 239
        except (IndexError, ValueError):
            return False


class PureProxyBackend(IStreamBackend):
    """Нативный Python-бэкенд для проксирования потоков.

    Без внешних бинарников. Работает напрямую через asyncio.

    Поддержка:
    - HTTP Bypass → mpegts.js
    - HLS Bypass → hls.js
    - UDP-to-HTTP → конвертация мультикаста в HTTP
    """

    def __init__(self, buffer_size: int = 65536) -> None:
        self._buffer_size = buffer_size
        self._sessions: Dict[str, ProxySession] = {}

    @property
    def backend_id(self) -> str:
        return "pure_proxy"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.PROXY, BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.HLS, StreamProtocol.UDP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HLS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск проксирующей сессии."""
        task_id = task.task_id or str(uuid.uuid4())[:8]

        try:
            session = ProxySession(
                task_id=task_id,
                input_url=task.input_url,
                protocol=task.input_protocol,
            )
            await session.start()
            self._sessions[task_id] = session

            logger.info(
                f"Pure Proxy [{task_id}]: {task.input_protocol.value} "
                f"'{task.input_url}' → {task.output_type.value}"
            )

            return StreamResult(
                task_id=task_id,
                success=True,
                backend_used="pure_proxy",
                output_url=f"/api/v1/m/stream/play/{task_id}",
                metadata={"protocol": task.input_protocol.value},
            )
        except Exception as e:
            logger.error(f"Pure Proxy [{task_id}] ошибка: {e}", exc_info=True)
            return StreamResult(
                task_id=task_id,
                success=False,
                backend_used="pure_proxy",
                error=str(e),
            )

    async def stop_stream(self, task_id: str) -> bool:
        """Остановка проксирующей сессии."""
        session = self._sessions.pop(task_id, None)
        if session:
            await session.stop()
            logger.info(f"Pure Proxy [{task_id}] остановлен")
            return True
        return False

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        # Превью не поддерживается
        return None

    async def is_available(self) -> bool:
        # Нативный Python — всегда доступен
        return True

    async def health_check(self) -> dict:
        return {
            "backend": "pure_proxy",
            "native": True,
            "active_sessions": len(self._sessions),
            "available": True,
        }

    def get_session(self, task_id: str) -> Optional[ProxySession]:
        """Получение активной сессии для чтения данных."""
        return self._sessions.get(task_id)


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Pure Proxy."""
    buffer_size = settings.get("proxy_buffer_size", 65536)
    return PureProxyBackend(buffer_size=buffer_size)
