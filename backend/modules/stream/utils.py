# Утилиты модуля stream: парсинг URL, определение протокола
import re
from urllib.parse import urlparse
from typing import Optional

from .core.types import StreamProtocol, OutputType, PreviewFormat
from .core.exceptions import InvalidStreamURLError


# Маппинг схем URL на протоколы
_SCHEME_TO_PROTOCOL = {
    "http": StreamProtocol.HTTP,
    "https": StreamProtocol.HTTP,
    "hls": StreamProtocol.HLS,
    "udp": StreamProtocol.UDP,
    "rtp": StreamProtocol.RTP,
    "rtsp": StreamProtocol.RTSP,
}

# Расширения, указывающие на HLS
_HLS_EXTENSIONS = {".m3u8", ".m3u"}


def detect_protocol(url: str) -> StreamProtocol:
    """Определение сетевого протокола по URL.

    Анализирует схему URL и расширение файла для
    корректного определения типа потока.

    Args:
        url: Сетевой адрес источника.

    Returns:
        StreamProtocol: Определённый протокол.

    Raises:
        InvalidStreamURLError: Если URL не является сетевым протоколом.
    """
    if not url:
        raise InvalidStreamURLError("Пустой URL")

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if not scheme:
        raise InvalidStreamURLError(
            f"URL без схемы: '{url}'. Ожидается сетевой протокол (http, udp, rtp, ...)"
        )

    # Проверка на локальный файл
    if scheme == "file":
        raise InvalidStreamURLError(
            f"Локальные файлы не поддерживаются: '{url}'"
        )

    protocol = _SCHEME_TO_PROTOCOL.get(scheme)
    if protocol is None:
        raise InvalidStreamURLError(
            f"Неподдерживаемый протокол '{scheme}' в URL: '{url}'"
        )

    # Уточнение: HTTP с .m3u8 расширением — это HLS
    if protocol == StreamProtocol.HTTP:
        path = parsed.path.lower()
        for ext in _HLS_EXTENSIONS:
            if path.endswith(ext):
                return StreamProtocol.HLS

    return protocol


def parse_output_type(value: str) -> OutputType:
    """Парсинг строки в тип вывода.

    Args:
        value: Строковое значение типа вывода.

    Returns:
        OutputType: Соответствующий тип.

    Raises:
        ValueError: Неизвестный тип вывода.
    """
    try:
        return OutputType(value.lower())
    except ValueError:
        valid = ", ".join(t.value for t in OutputType)
        raise ValueError(
            f"Неизвестный тип вывода: '{value}'. Допустимые: {valid}"
        )


def parse_preview_format(value: str) -> PreviewFormat:
    """Парсинг строки в формат превью.

    Args:
        value: Строковое значение формата (jpeg, png, webp).

    Returns:
        PreviewFormat: Соответствующий формат.

    Raises:
        ValueError: Неизвестный формат превью.
    """
    try:
        return PreviewFormat(value.lower())
    except ValueError:
        valid = ", ".join(f.value for f in PreviewFormat)
        raise ValueError(
            f"Неизвестный формат превью: '{value}'. Допустимые: {valid}"
        )


def validate_network_url(url: str) -> bool:
    """Валидация URL: проверяет, что это сетевой адрес.

    Returns:
        True, если URL содержит валидную сетевую схему.
    """
    try:
        detect_protocol(url)
        return True
    except InvalidStreamURLError:
        return False
