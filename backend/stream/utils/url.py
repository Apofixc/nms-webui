"""Нормализация URL потоков: фрагмент, хост 0 для HTTP, UDP."""
from __future__ import annotations


def normalize_stream_url(url: str, stream_host: str | None = None) -> str:
    """
    Нормализация URL потока из output канала или ручного ввода.
    - Убирает фрагмент (#keep_active, #sync&cbr=4 и т.п.) для всех схем.
    - HTTP/HTTPS: хост «0» заменяется на stream_host или 127.0.0.1.
    - UDP: только фрагмент; адрес/порт не меняются.
    - Остальные схемы (rtp, rtsp, srt, tcp, file): только фрагмент.
    """
    if not url or not isinstance(url, str):
        return url
    from urllib.parse import urlparse, urlunparse

    u = url.strip()
    parsed = urlparse(u)
    scheme = parsed.scheme.lower() if parsed.scheme else ""
    # Убрать фрагмент везде
    new_fragment = ""

    if scheme in ("http", "https"):
        netloc = parsed.netloc
        if netloc.startswith("0:") or netloc == "0":
            host = (stream_host or "127.0.0.1").strip()
            port_part = ":" + netloc.split(":", 1)[1] if ":" in netloc else ""
            netloc = host + port_part
        return urlunparse((scheme, netloc, parsed.path or "/", parsed.params, parsed.query, new_fragment))

    if scheme == "udp":
        # Только убрать фрагмент; не менять адрес/порт
        return urlunparse((scheme, parsed.netloc, parsed.path or "", parsed.params, parsed.query, new_fragment))

    # Остальные схемы: rtp, rtsp, srt, tcp, file и т.д. — убрать фрагмент
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path or "", parsed.params, parsed.query, new_fragment))
