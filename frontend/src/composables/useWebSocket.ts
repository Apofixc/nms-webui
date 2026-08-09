/**
 * Composable for WebSocket real-time events.
 * Features:
 * - Multi-Tab Leader Election via BroadcastChannel (1 WS per browser)
 * - Safe JWT Auth via Sec-WebSocket-Protocol
 * - Immediate and Batched Event Handling
 * - Reconnection Event Replay (last_event_id)
 * - Global window.NMS.events API for dynamic widgets
 */
import { ref, getCurrentInstance, onMounted, onUnmounted } from 'vue'
import { getStoredToken } from '@/core/auth'
import { createWsClient, type WsClient } from '@/core/websocket'

const isConnected = ref(false)
const lastEvent = ref<any>(null)
let wsClient: WsClient | null = null

let pingInterval: any = null
let reconnectTimeout: any = null
let subscriberCount = 0
let lastSeenSeqId = 0

type EventCallback = (data: any) => void
interface ListenerItem {
    eventType?: string
    callback: EventCallback
}
const listeners = new Set<ListenerItem>()
let wasDisconnected = false

// --- Multi-Tab Leader Election via BroadcastChannel ---
let isLeader = false
let leaderElectionTimeout: any = null
let broadcastChannel: BroadcastChannel | null = null

function initBroadcastChannel() {
    if (broadcastChannel || typeof window === 'undefined' || !('BroadcastChannel' in window)) return

    broadcastChannel = new BroadcastChannel('nms_ws_broadcast_channel')

    broadcastChannel.onmessage = (event) => {
        const msg = event.data
        if (!msg) return

        if (msg.type === '__who_is_leader__') {
            if (isLeader) {
                broadcastChannel?.postMessage({ type: '__i_am_leader__' })
            }
        } else if (msg.type === '__i_am_leader__') {
            if (!isLeader) {
                if (leaderElectionTimeout) clearTimeout(leaderElectionTimeout)
            }
        } else if (msg.type === '__leader_closing__') {
            if (!isLeader) {
                claimLeadership()
            }
        } else if (msg.type === '__ws_event__') {
            // Ведомые вкладки получают события от лидера
            processIncomingData(msg.payload, false)
        } else if (msg.type === '__ws_status__') {
            isConnected.value = msg.connected
        }
    }

    window.addEventListener('beforeunload', () => {
        if (isLeader) {
            broadcastChannel?.postMessage({ type: '__leader_closing__' })
        }
    })
}

function startLeaderElection() {
    initBroadcastChannel()
    if (!broadcastChannel) {
        // Если BroadcastChannel не поддерживается браузером, подключаем сокет напрямую
        connectSocket()
        return
    }

    broadcastChannel.postMessage({ type: '__who_is_leader__' })
    leaderElectionTimeout = setTimeout(() => {
        claimLeadership()
    }, 300)
}

function claimLeadership() {
    isLeader = true
    connectSocket()
}

function processSingleEvent(data: any) {
    if (!data) return
    if (data.seq_id && typeof data.seq_id === 'number') {
        lastSeenSeqId = Math.max(lastSeenSeqId, data.seq_id)
    }

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
}

function processIncomingData(data: any, isFromDirectSocket: boolean = true) {
    if (!data) return

    if (data.type === 'pong') {
        return
    }

    // Если событие получено лидером напрямую с сокета, пересылаем ведомым вкладкам
    if (isFromDirectSocket && broadcastChannel && isLeader) {
        broadcastChannel.postMessage({ type: '__ws_event__', payload: data })
        broadcastChannel.postMessage({ type: '__ws_status__', connected: true })
    }

    // Разбор батча
    if (data.type === 'batch' && Array.isArray(data.events)) {
        data.events.forEach((evt: any) => processSingleEvent(evt))
        return
    }

    // Разбор досланного массива событий при реконнекте
    if (data.type === 'replay' && Array.isArray(data.events)) {
        data.events.forEach((evt: any) => processSingleEvent(evt))
        return
    }

    processSingleEvent(data)
}

function connectSocket() {
    if (wsClient && wsClient.isConnected()) return

    wsClient = createWsClient({
        url: '/api/events/ws',
        useTokenAuth: true,
        autoReconnect: true,
        onOpen: () => {
            const isReconnect = wasDisconnected
            isConnected.value = true
            wasDisconnected = false

            if (broadcastChannel && isLeader) {
                broadcastChannel.postMessage({ type: '__ws_status__', connected: true })
            }

            // Если было переподключение, отправляем handshake для досылки пропущенных сообщений
            if (lastSeenSeqId > 0 && wsClient && wsClient.isConnected()) {
                wsClient.send({ type: 'resume', last_event_id: lastSeenSeqId })
            }

            if (isReconnect) {
                const reconnectedData = { type: 'ws_reconnected' }
                processIncomingData(reconnectedData, true)
            }
        },
        onMessage: (data) => {
            processIncomingData(data, true)
        },
        onClose: () => {
            isConnected.value = false
            wasDisconnected = true
            if (broadcastChannel && isLeader) {
                broadcastChannel.postMessage({ type: '__ws_status__', connected: false })
            }
        },
        onError: () => {
            isConnected.value = false
            wasDisconnected = true
        },
    })
}

/**
 * Standalone subscription for dynamic modules & widgets.
 */
export function subscribe(eventType: string | null, callback: EventCallback): () => void {
    if (subscriberCount === 0) {
        startLeaderElection()
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
            if (wsClient) {
                wsClient.close()
                wsClient = null
            }
        }
    }
}

/**
 * Send raw text or JSON object over WebSocket.
 */
export function send(data: string | object): boolean {
    if (wsClient && wsClient.isConnected()) {
        wsClient.send(data)
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
            startLeaderElection()
        }
        subscriberCount++
    })

    onUnmounted(() => {
        subscriberCount--
        if (subscriberCount <= 0) {
            subscriberCount = 0
            if (reconnectTimeout) clearTimeout(reconnectTimeout)
            if (pingInterval) clearInterval(pingInterval)
            if (wsClient) {
                wsClient.close()
                wsClient = null
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
