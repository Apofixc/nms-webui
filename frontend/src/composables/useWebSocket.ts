/**
 * Composable for WebSocket real-time events.
 */
import { ref, onMounted, onUnmounted } from 'vue'

export function useWebSocket() {
    const isConnected = ref(false)
    const lastEvent = ref<any>(null)
    let ws: WebSocket | null = null
    let pingInterval: any = null

    function connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${protocol}//${window.location.host}/api/events/ws`

        ws = new WebSocket(wsUrl)

        ws.onopen = () => {
            isConnected.value = true
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
            // Auto reconnect after 5s
            setTimeout(connect, 5000)
        }

        ws.onerror = () => {
            isConnected.value = false
        }
    }

    onMounted(() => {
        connect()
    })

    onUnmounted(() => {
        if (pingInterval) clearInterval(pingInterval)
        if (ws) ws.close()
    })

    return {
        isConnected,
        lastEvent,
    }
}
