"""Прокси UDP → HTTP: чтение UDP-потока (MPEG-TS) и отдача в HTTP без внешних программ."""
from __future__ import annotations

import asyncio
import socket
import struct
import threading
from queue import Empty, Queue
from typing import AsyncIterator, Callable, Optional, Union


def is_udp_url(url: str) -> bool:
    """Проверка, что URL — UDP (udp://...)."""
    if not url or not isinstance(url, str):
        return False
    return url.strip().lower().startswith("udp://")


def parse_udp_url(url: str) -> tuple[str, int, Optional[str]]:
    """
    Парсинг UDP URL. Возвращает (bind_addr, port, multicast_group).
    - udp://@239.0.0.1:1234 → ('', 1234, '239.0.0.1')
    - udp://:1234 или udp://0.0.0.0:1234 → ('', 1234, None)
    - udp://host:port (unicast) → ('', port, None); host не используется для bind.
    """
    url = url.strip()
    if not url.lower().startswith("udp://"):
        raise ValueError("Not a UDP URL")
    rest = url[6:].lstrip("/")
    host = None
    port = None
    if rest.startswith("@"):
        rest = rest[1:]
    if ":" in rest:
        part, port_str = rest.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port in UDP URL: {port_str}")
        host = part or None
    else:
        try:
            port = int(rest)
        except ValueError:
            raise ValueError(f"Invalid port in UDP URL: {rest}")
    if port is None or port < 1 or port > 65535:
        raise ValueError("Invalid port")
    bind_addr = ""
    mcast = None
    if host:
        try:
            socket.inet_aton(host)
            if host.startswith("224.") or host.startswith("239.") or host == "224.0.0.0":
                mcast = host
        except OSError:
            pass
    return (bind_addr, port, mcast)


def _udp_receiver(
    udp_url: str,
    chunk_queue: Queue[bytes],
    stop_event: threading.Event,
    timeout_sec: float = 10.0,
) -> None:
    """
    Поток: читает UDP и кладёт пакеты в chunk_queue. При stop_event выходит.
    """
    try:
        bind_addr, port, mcast = parse_udp_url(udp_url)
    except ValueError:
        chunk_queue.put(b"")
        return
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        sock.settimeout(1.0)
        sock.bind((bind_addr, port))
        if mcast:
            mreq = struct.pack("4sl", socket.inet_aton(mcast), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        while not stop_event.is_set():
            try:
                data = sock.recv(65535)
                if not data:
                    break
                chunk_queue.put(data)
            except socket.timeout:
                continue
            except OSError:
                break
    except Exception:
        chunk_queue.put(b"")
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


async def stream_udp_to_http(
    udp_url: str,
    request_disconnected: Optional[Callable[[], Union[bool, object]]] = None,
    chunk_timeout: float = 15.0,
) -> AsyncIterator[bytes]:
    """
    Асинхронный генератор: читает UDP и отдаёт байты. Без внешних программ.
    request_disconnected — опционально awaitable/callable, при True прекращаем.
    """
    chunk_queue: Queue[bytes] = Queue()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_udp_receiver,
        args=(udp_url, chunk_queue, stop_event, chunk_timeout),
        daemon=True,
    )
    thread.start()
    try:
        while True:
            try:
                chunk = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: chunk_queue.get(timeout=0.5),
                )
            except Empty:
                if request_disconnected is not None:
                    try:
                        disc = request_disconnected()
                        if asyncio.iscoroutine(disc):
                            disc = await disc
                        if disc:
                            break
                    except Exception:
                        pass
                continue
            if not chunk:
                break
            yield chunk
    finally:
        stop_event.set()
        thread.join(timeout=2.0)


def stream_udp_to_file_sync(
    udp_url: str,
    output_path: str,
    *,
    duration_sec: float = 3.0,
    max_bytes: Optional[int] = 2 * 1024 * 1024,
) -> None:
    """
    Синхронно читать UDP и писать MPEG-TS в файл. Для захвата одного кадра (превью):
    потом передать файл в FFmpeg/VLC и т.д.
    duration_sec — максимум секунд чтения; max_bytes — максимум байт (по умолчанию 2 МБ).
    """
    bind_addr, port, mcast = parse_udp_url(udp_url)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (AttributeError, OSError):
        pass
    sock.settimeout(1.0)
    try:
        sock.bind((bind_addr, port))
        if mcast:
            mreq = struct.pack("4sl", socket.inet_aton(mcast), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        import time
        deadline = time.monotonic() + duration_sec
        written = 0
        with open(output_path, "wb") as f:
            while time.monotonic() < deadline and (max_bytes is None or written < max_bytes):
                try:
                    data = sock.recv(65535)
                    if not data:
                        break
                    f.write(data)
                    written += len(data)
                except socket.timeout:
                    if written > 0:
                        break
                    continue
                except OSError:
                    break
    finally:
        sock.close()
