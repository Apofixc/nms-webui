<template>
  <div class="relative w-full h-full bg-black flex items-center justify-center overflow-hidden">
    <video
      ref="videoRef"
      class="w-full h-full object-contain"
      controls
      autoplay
      :muted="muted"
      playsinline
      crossOrigin="anonymous"
    ></video>
    
    <div v-if="error" class="absolute inset-0 flex items-center justify-center bg-black/80 p-4 text-center">
      <div class="text-danger flex flex-col items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span class="text-sm font-medium">{{ error }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import Hls from 'hls.js'
import mpegts from 'mpegts.js'

const props = defineProps<{
  url: string
  type?: 'hls' | 'http_ts' | 'http' | 'webrtc' | string
  muted?: boolean
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const error = ref<string | null>(null)

let hlsPlayer: Hls | null = null
let mpegtsPlayer: any = null

function initPlayer() {
  destroyPlayer()
  error.value = null

  if (!videoRef.value || !props.url) return

  const video = videoRef.value

  // HLS
  if (props.type === 'hls' || props.url.includes('.m3u8')) {
    if (Hls.isSupported()) {
      hlsPlayer = new Hls({
        enableWorker: true,
        lowLatencyMode: false, // Отключаем, так как наш бэкенд пока не LL-HLS
        backBufferLength: 60,
        maxBufferLength: 30,
        liveSyncDurationCount: 2, // Начинать играть после накопления 2 сегментов (быстрее старт)
        liveMaxLatencyDurationCount: 5,
      })
      hlsPlayer.loadSource(props.url)
      hlsPlayer.attachMedia(video)
      
      hlsPlayer.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {
          // Если автозапуск заблокирован (нужен mute)
          if (video.muted) {
            console.warn('HLS Autoplay failed even when muted')
          }
        })
      })

      hlsPlayer.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              error.value = 'Ошибка сети при загрузке HLS потока'
              hlsPlayer?.startLoad()
              break
            case Hls.ErrorTypes.MEDIA_ERROR:
              hlsPlayer?.recoverMediaError()
              break
            default:
              error.value = 'Критическая ошибка HLS: ' + data.details
              destroyPlayer()
              break
          }
        }
      })
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS (Safari)
      video.src = props.url
      video.addEventListener('error', () => {
        error.value = 'Ошибка воспроизведения HLS (Native)'
      })
    } else {
      error.value = 'HLS не поддерживается в этом браузере'
    }
  } 
  // HTTP-TS / HTTP (MPEG-TS)
  else if (props.type === 'http_ts' || props.type === 'http') {
    if (mpegts.getFeatureList().mseLivePlayback) {
      mpegtsPlayer = mpegts.createPlayer({
        type: 'mse', // mpegts
        isLive: true,
        url: props.url
      }, {
        enableStashBuffer: false,
        liveBufferLatencyChasing: true,
      })
      mpegtsPlayer.attachMediaElement(video)
      mpegtsPlayer.load()
      mpegtsPlayer.play().catch((e: any) => {
        error.value = 'Ошибка запуска MPEG-TS: ' + e.message
      })
      mpegtsPlayer.on(mpegts.Events.ERROR, (errType: string, errDetail: string) => {
        error.value = `MPEG-TS Ошибка: ${errType} - ${errDetail}`
      })
    } else {
      // Fallback
      video.src = props.url
    }
  }
  // Fallback for native formats
  else {
    video.src = props.url
    video.addEventListener('error', () => {
      error.value = 'Ошибка воспроизведения медиа'
    })
  }
}

function destroyPlayer() {
  if (hlsPlayer) {
    hlsPlayer.destroy()
    hlsPlayer = null
  }
  if (mpegtsPlayer) {
    mpegtsPlayer.destroy()
    mpegtsPlayer = null
  }
  if (videoRef.value) {
    videoRef.value.removeAttribute('src')
    videoRef.value.load()
  }
}

watch(() => props.url, () => {
  initPlayer()
})

onMounted(() => {
  initPlayer()
})

onBeforeUnmount(() => {
  destroyPlayer()
})
</script>
