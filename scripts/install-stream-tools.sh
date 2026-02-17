#!/usr/bin/env bash
# Установка инструментов для захвата и воспроизведения потоков (превью, HTTP/UDP → HLS):
# FFmpeg, VLC, GStreamer, TSDuck.
# Запуск: sudo ./scripts/install-stream-tools.sh

set -e

echo "=== Обновление списка пакетов ==="
apt-get update -qq

echo ""
echo "=== Установка FFmpeg (захват кадра, конвертация в HLS) ==="
apt-get install -y ffmpeg
ffmpeg -version | head -1

echo ""
echo "=== Установка VLC (резервный бэкенд для захвата кадра) ==="
apt-get install -y vlc-nox || apt-get install -y vlc
# Проверка без GUI
which vlc && echo "VLC установлен"

echo ""
echo "=== Установка GStreamer (резервный бэкенд для захвата) ==="
apt-get install -y \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav
gst-launch-1.0 --version 2>/dev/null | head -1 || true

echo ""
echo "=== Установка TSDuck (анализ и работа с MPEG-TS) ==="
# Пакеты: https://tsduck.io/tsduck-binaries/
ARCH=$(dpkg --print-architecture)
if command -v tsp >/dev/null 2>&1; then
  echo "TSDuck уже установлен: $(tsp --version 2>/dev/null | head -1)"
else
  if apt-cache show tsduck >/dev/null 2>&1; then
    apt-get install -y tsduck
  else
    TSDUCK_TAG="v3.43-4549"
    TSDUCK_REPO="https://github.com/tsduck/tsduck/releases/download/$TSDUCK_TAG"
    # Runtime-пакеты (tsduck_*, не tsduck-dev) — см. https://tsduck.io/tsduck-binaries/
    case "$ARCH" in
      amd64|x86_64) TSDUCK_DEB="tsduck_3.43-4549.ubuntu24_amd64.deb" ;;
      arm64|aarch64) TSDUCK_DEB="tsduck_3.43-4549.ubuntu24_arm64.deb" ;;
      *) TSDUCK_DEB="tsduck_3.43-4549.debian13_${ARCH}.deb" ;;
    esac
    # URL-кодирование подчёркивания для GitHub
    TSDUCK_URL="$TSDUCK_REPO/${TSDUCK_DEB//_/%5F}"
    TMPD=$(mktemp -d)
    trap "rm -rf $TMPD" EXIT
    echo "Скачивание TSDuck: $TSDUCK_DEB"
    if wget -q -O "$TMPD/$TSDUCK_DEB" "$TSDUCK_URL" 2>/dev/null; then
      dpkg -i "$TMPD/$TSDUCK_DEB" || apt-get install -f -y
      echo "TSDuck установлен."
    else
      echo "Не удалось скачать. Ссылки: https://tsduck.io/tsduck-binaries/"
      echo "  или: $TSDUCK_REPO/$TSDUCK_DEB"
    fi
  fi
fi

echo ""
echo "=== Проверка ==="
echo -n "FFmpeg: "; which ffmpeg && ffmpeg -version 2>/dev/null | head -1
echo -n "VLC:    "; which vlc 2>/dev/null || echo "не найден"
echo -n "GStreamer: "; which gst-launch-1.0 2>/dev/null || echo "не найден"
echo -n "TSDuck: "; which tsp 2>/dev/null && tsp --version 2>/dev/null | head -1 || echo "не найден"

echo ""
echo "Готово. Для превью и воспроизведения в браузере используется FFmpeg (HLS)."
echo "VLC и GStreamer — резервные бэкенды для захвата кадра."
