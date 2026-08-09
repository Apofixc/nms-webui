/**
 * Composable for WebSocket real-time events.
 * Singleton pattern for shared socket connection.
 * Supports Vue lifecycle auto-cleanup, standalone subscriptions,
 * and global window API for dynamic modules & widgets.
 */
import { ref, getCurrentInstance, onMounted, onUnmounted } from 'vue'
import { getStoredToken } from '@/core/auth'

const isConnected = ref(false)
const lastEvent = ref<any>(null)
let ws: WebSocket | null = null
let pingInterval: any = null
let reconnectTimeout: any = null
let subscriberCount = 0

type EventCallback = (data: any) => void
interface ListenerItem {
    eventType?: string
    callback: EventCallback
}
const listeners = new Set<ListenerItem>()

let wasDisconnected = false

function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    let wsUrl = `${protocol}//${window.location.host}/api/events/ws`
    const token = getStoredToken()
    if (token) {
        wsUrl += `?token=${encodeURIComponent(token)}`
    }

    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
        const isReconnect = wasDisconnected
        isConnected.value = true
        wasDisconnected = false

        if (pingInterval) clearInterval(pingInterval)
        pingInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send('ping')
            }
        }, 25000)

        if (isReconnect) {
            const reconnectedData = { type: 'ws_reconnected' }
            lastEvent.value = reconnectedData
            listeners.forEach((item) => {
                if (!item.eventType || item.eventType === 'ws_reconnected') {
                    try {
                        item.callback(reconnectedData)
                    } catch (err) {
                        console.error('[WS] Reconnect listener error:', err)
                    }
                }
            })
        }
    }

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data)
            if (data.type === 'pong') return
            lastEvent.value = data
            listeners.forEach((item) => {
                if (!item.eventType || item.eventType === data.type) {
                    try {
                        item.callback(data)
                    } catch (err) {
                        console.error('[WS] Event listener error:', err)
                    }
                }
            })
        } catch {
            // ignore text msgs
        }
    }

    ws.onclose = () => {
        isConnected.value = false
        wasDisconnected = true
        if (pingInterval) clearInterval(pingInterval)
        if (subscriberCount > 0) {
            reconnectTimeout = setTimeout(connect, 5000)
        }
    }

    ws.onerror = () => {
        isConnected.value = false
        wasDisconnected = true
    }
}

/**
 * Low-level standalone subscription for dynamic modules & widgets outside Vue setup scope.
 * Automatically manages shared WS connection count.
 */
export function subscribe(eventType: string | null, callback: EventCallback): () => void {
    if (subscriberCount === 0) {
        connect()
    }
    subscriberCount++

    const item: ListenerItem = {
        eventType: eventType || undefined,
        callback,
    }
    listeners.add(item)

    let cleanedUp = false
    return function unsubscribe() {
        if (cleanedUp) return
        cleanedUp = true
        listeners.delete(item)
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
    }
}

/**
 * Send raw text or JSON object over WebSocket.
 */
export function send(data: string | object): boolean {
    if (ws && ws.readyState === WebSocket.OPEN) {
        const payload = typeof data === 'string' ? data : JSON.stringify(data)
        ws.send(payload)
        return true
    }
    return false
}

/**
 * Vue Composable for WebSocket real-time events.
 */
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

    function onEvent(eventType: string | null, callback: EventCallback) {
        const unsub = subscribe(eventType, callback)
        if (getCurrentInstance()) {
            onUnmounted(() => {
                unsub()
            })
        }
        return unsub
    }

    return {
        isConnected,
        lastEvent,
        onEvent,
        subscribe,
        send,
    }
}

// Global API exposure for dynamic modules and widgets loaded at runtime
if (typeof window !== 'undefined') {
    const win = window as any
    win.NMS = win.NMS || {}
    win.NMS.events = {
        subscribe,
        send,
        useWebSocket,
        isConnected,
        lastEvent,
    }
}


