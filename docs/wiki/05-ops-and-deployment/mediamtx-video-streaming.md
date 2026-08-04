# [Roadmap] Интеграция Видеостриминга MediaMTX

> [!NOTE]
> **Статус подсистемы**: *Roadmap / Запланировано в будущих релизах*. Данная статья описывает целевую архитектуру и прототип интеграции видеопотоков от IP-камер.

---

## 📹 Целевая архитектура видеостриминга

В будущих версиях NMS WebUI планируется интеграция медиасервера **MediaMTX** (rtsp-simple-server) для трансляции видео с IP-камер видеонаблюдения без нагрузи на основной Python бэкенд.

```text
┌──────────────────┐       RTSP        ┌─────────────────┐      WebRTC / HLS      ┌─────────────────┐
│ IP Камера / RTSP │ ────────────────► │ MediaMTX Server │ ────────────────────► │ NMS WebUI Player│
└──────────────────┘                   └─────────────────┘                        └─────────────────┘
```

---

## ⚙️ Планируемая конфигурация MediaMTX (`mediamtx.yml`)

Конфигурационный файл будет располагаться в корне проекта: `/opt/nms-webui/mediamtx.yml`.

### Планируемые порты и протоколы:
- **RTSP Server**: `8554` (`rtsp://localhost:8554/<stream_name>`)
- **WebRTC (Whip/Whep)**: `8889` (`http://localhost:8889/<stream_name>`)
- **HLS / Low Latency HLS**: `8888` (`http://localhost:8888/<stream_name>/index.m3u8`)
- **API управления**: `9997` (`http://localhost:9997/v3/...`)

---

## 🌐 Шаблон интеграции плееров во Vue 3

Для будущей интеграции видеоплееров в модулях рекомендуется использовать прототип на базе HLS.js или WebRTC:

```vue
<template>
  <div class="video-container rounded-xl overflow-hidden border border-outline-variant/60">
    <video ref="videoRef" controls autoplay muted class="w-full h-auto"></video>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import Hls from 'hls.js'

const props = defineProps<{ streamName: string }>()
const videoRef = ref<HTMLVideoElement | null>(null)
let hls: Hls | null = null

onMounted(() => {
  const streamUrl = `http://${window.location.hostname}:8888/${props.streamName}/index.m3u8`
  
  if (Hls.isSupported() && videoRef.value) {
    hls = new Hls()
    hls.loadSource(streamUrl)
    hls.attachMedia(videoRef.value)
  } else if (videoRef.value?.canPlayType('application/vnd.apple.mpegurl')) {
    videoRef.value.src = streamUrl
  }
})

onBeforeUnmount(() => {
  if (hls) {
    hls.destroy()
  }
})
</script>
```

---

## 📋 Статус разработки
- [ ] Интеграция бинарного исполняемого файла MediaMTX в `run_webui.sh`.
- [ ] API бэкенда для динамического добавления RTSP потоков камер через API MediaMTX (порт `9997`).
- [ ] Готовый Vue 3 компонент `VideoPlayerWidget.vue` в дизайн-системе.
