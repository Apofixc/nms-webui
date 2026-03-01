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

    <!-- WebRTC Loading State -->
    <div v-if="webrtcConnecting" class="absolute inset-0 flex flex-col items-center justify-center bg-black/40 backdrop-blur-sm">
       <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin mb-3"></div>
       <span class="text-white text-xs font-medium">Установка WebRTC соединения...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import Hls from 'hls.js'
import mpegts from 'mpegts.js'
import http from '@/core/api'

const props = defineProps<{
  url: string
  type?: 'hls' | 'http_ts' | 'http' | 'webrtc' | string
  muted?: boolean
  metadata?: any
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const error = ref<string | null>(null)
const webrtcConnecting = ref(false)

let hlsPlayer: Hls | null = null
let mpegtsPlayer: any = null
let pc: RTCPeerConnection | null = null

async function initPlayer() {
  destroyPlayer()
  error.value = null

  if (!videoRef.value || !props.url) return

  const video = videoRef.value

  // WebRTC
  if (props.type === 'webrtc') {
    await initWebRTC()
    return
  }

  // HLS
  if (props.type === 'hls' || props.url.includes('.m3u8')) {
    if (Hls.isSupported()) {
      hlsPlayer = new Hls({
        enableWorker: true,
        lowLatencyMode: false,
        backBufferLength: 60,
        maxBufferLength: 30,
        liveSyncDurationCount: 2,
        liveMaxLatencyDurationCount: 5,
      })
      hlsPlayer.loadSource(props.url)
      hlsPlayer.attachMedia(video)
      
      hlsPlayer.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {})
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
      video.src = props.url
    } else {
      error.value = 'HLS не поддерживается в этом браузере'
    }
  } 
  // HTTP-TS / HTTP (MPEG-TS)
  else if (props.type === 'http_ts' || props.type === 'http') {
    if (mpegts.getFeatureList().mseLivePlayback) {
      mpegtsPlayer = mpegts.createPlayer({
        type: 'mse',
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
    } else {
      video.src = props.url
    }
  }
  else {
    video.src = props.url
    video.addEventListener('error', () => {
      error.value = 'Ошибка воспроизведения медиа'
    })
  }
}

async function initWebRTC() {
  if (!videoRef.value) return
  webrtcConnecting.value = true
  
  try {
    pc = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
      ]
    })

    pc.ontrack = (event) => {
      if (videoRef.value) {
        videoRef.value.srcObject = event.streams[0]
      }
    }

    pc.oniceconnectionstatechange = () => {
      console.log('WebRTC ICE State:', pc?.iceConnectionState)
      if (pc?.iceConnectionState === 'connected') {
        webrtcConnecting.value = false
      } else if (pc?.iceConnectionState === 'failed') {
        webrtcConnecting.value = false
        error.value = 'WebRTC соединение не удалось установить'
      }
    }

    // Получаем Offer из metadata или через GET если нет в metadata
    let offer = props.metadata?.sdp_offer
    if (!offer) {
      const response = await http.get(props.url) // props.url points to signaling endpoint
      offer = response.data
    }

    if (!offer) throw new Error('Не удалось получить SDP Offer')

    await pc.setRemoteDescription(new RTCSessionDescription(offer))
    const answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    // Отправляем Answer на бэкенд
    await http.post(props.url, {
      sdp: pc.localDescription?.sdp,
      type: pc.localDescription?.type
    })

  } catch (e: any) {
    console.error('WebRTC Init Error:', e)
    error.value = 'Ошибка WebRTC: ' + (e.message || 'неизвестная ошибка')
    webrtcConnecting.value = false
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
  if (pc) {
    pc.close()
    pc = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
    videoRef.value.removeAttribute('src')
    videoRef.value.load()
  }
  webrtcConnecting.value = false
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
