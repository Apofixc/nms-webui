/**
 * Composable for WebSocket real-time events.
 * Singleton pattern for shared socket connection.
 */
import { ref, onMounted, onUnmounted } from 'vue'

const isConnected = ref(false)
const lastEvent = ref<any>(null)
let ws: WebSocket | null = null
let pingInterval: any = null
let reconnectTimeout: any = null
let subscriberCount = 0

function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/events/ws`

    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
        isConnected.value = true
        if (pingInterval) clearInterval(pingInterval)
        pingInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send('ping')
            }
        }, 25000)
    }

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data)
            if (data.type === 'pong') return
            lastEvent.value = data
        } catch {
            // ignore text msgs
        }
    }

    ws.onclose = () => {
        isConnected.value = false
        if (pingInterval) clearInterval(pingInterval)
        if (subscriberCount > 0) {
            reconnectTimeout = setTimeout(connect, 5000)
        }
    }

    ws.onerror = () => {
        isConnected.value = false
    }
}

export function useWebSocket() {
    onMounted(() => {
        if (subscriberCount === 0) {
            connect()
        }
        subscriberCount++
    })

    onUnmounted(() => {
        subscriberCount--
        if (subscriberCount <= 0) {
            subscriberCount = 0
            if (reconnectTimeout) clearTimeout(reconnectTimeout)
            if (pingInterval) clearInterval(pingInterval)
            if (ws) {
                ws.close()
                ws = null
            }
        }
    })

    return {
        isConnected,
        lastEvent,
    }
}

