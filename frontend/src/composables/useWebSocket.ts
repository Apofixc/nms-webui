import { ref, computed, getCurrentInstance, onMounted, onUnmounted } from 'vue'
import { createWsClient, type WsClient } from '@/core/websocket'
import { ensureAuthStatus, clearAuthSession } from '@/core/auth'

const isConnected = ref(false)
const lastEvent = ref<any>(null)
const rtt = ref<number | null>(null)

const connectionQuality = computed(() => {
    if (!isConnected.value) return 'disconnected'
    if (rtt.value === null) return 'good'
    if (rtt.value < 50) return 'excellent'
    if (rtt.value < 150) return 'good'
    return 'poor'
})

let wsClient: WsClient | null = null

let subscriberCount = 0
let lastSeenSeqId = 0

type EventCallback = (data: any) => void
interface ListenerItem {
    eventType?: string
    callback: EventCallback
}
const listeners = new Set<ListenerItem>()
const activeTopics = new Map<string, number>()
const pendingAckCallbacks = new Map<string, { resolve: (val: any) => void; reject: (err: any) => void; timer: any }>()
let wasDisconnected = false

// --- Multi-Tab Leader Election via Web Locks API + BroadcastChannel ---
let isLeader = false
const isLeaderRef = ref(false)
let leaderElectionTimeout: any = null
let broadcastChannel: BroadcastChannel | null = null
let leaderLockResolver: (() => void) | null = null

function updateLeaderStatusBroadcast() {
    if (broadcastChannel && isLeader) {
        const currentRtt = wsClient ? wsClient.getRtt() : null
        rtt.value = currentRtt
        broadcastChannel.postMessage({
            type: '__ws_status__',
            connected: isConnected.value,
            rtt: currentRtt,
        })
    }
}

function initBroadcastChannel() {
    if (broadcastChannel || typeof window === 'undefined' || !('BroadcastChannel' in window)) return

    broadcastChannel = new BroadcastChannel('nms_ws_broadcast_channel')

    broadcastChannel.onmessage = (event) => {
        const msg = event.data
        if (!msg) return

        if (msg.type === '__who_is_leader__') {
            if (isLeader) {
                broadcastChannel?.postMessage({ type: '__i_am_leader__' })
                updateLeaderStatusBroadcast()
            }
        } else if (msg.type === '__i_am_leader__') {
            if (!isLeader && leaderElectionTimeout) {
                clearTimeout(leaderElectionTimeout)
            }
        } else if ((msg.type === '__request_topics__' || msg.type === '__i_am_leader__') && !isLeader) {
            if (activeTopics.size > 0 && broadcastChannel) {
                activeTopics.forEach((_, topic) => {
                    broadcastChannel?.postMessage({
                        type: '__ws_send__',
                        payload: { type: 'subscribe', topic },
                    })
                })
            }
        } else if (msg.type === '__leader_closing__') {
            if (!isLeader) {
                claimLeadership()
            }
        } else if (msg.type === '__ws_event__') {
            // Ведомые вкладки получают события от лидера
            processIncomingData(msg.payload, false)
        } else if (msg.type === '__ws_status__') {
            isConnected.value = !!msg.connected
            if (msg.rtt !== undefined) {
                rtt.value = msg.rtt
            }
        } else if (msg.type === '__ws_ping__' && isLeader) {
            if (wsClient) wsClient.ping()
        } else if (msg.type === '__ws_send__' && isLeader) {
            // Проксирование сообщений с ведомой вкладки лидеру и регистрация топиков в activeTopics Лидера
            if (msg.payload) {
                if (typeof msg.payload === 'object' && msg.payload.topic) {
                    const topic = String(msg.payload.topic)
                    if (msg.payload.type === 'subscribe') {
                        const count = (activeTopics.get(topic) || 0) + 1
                        activeTopics.set(topic, count)
                    } else if (msg.payload.type === 'unsubscribe') {
                        const count = (activeTopics.get(topic) || 0) - 1
                        if (count <= 0) activeTopics.delete(topic)
                        else activeTopics.set(topic, count)
                    }
                }
                send(msg.payload)
            }
        }
    }

    window.addEventListener('beforeunload', () => {
        if (isLeader) {
            broadcastChannel?.postMessage({ type: '__leader_closing__' })
            releaseLeadership()
        }
    })
}

function startLeaderElection() {
    initBroadcastChannel()

    if (broadcastChannel && !isLeader) {
        broadcastChannel.postMessage({ type: '__who_is_leader__' })
    }

    // 1. Предпочтительный путь: Web Locks API (автоматический failover при краше вкладки)
    if (typeof navigator !== 'undefined' && 'locks' in navigator && navigator.locks.request) {
        navigator.locks.request('nms_ws_leader_lock', async () => {
            claimLeadership()
            return new Promise<void>((resolve) => {
                leaderLockResolver = resolve
            })
        }).catch((err) => {
            console.warn('[WS] Web Lock request error, falling back to BroadcastChannel:', err)
            fallbackBroadcastElection()
        })
        return
    }

    // 2. Фолбэк путь: BroadcastChannel
    fallbackBroadcastElection()
}

function fallbackBroadcastElection() {
    if (!broadcastChannel) {
        connectSocket()
        return
    }

    broadcastChannel.postMessage({ type: '__who_is_leader__' })
    leaderElectionTimeout = setTimeout(() => {
        claimLeadership()
    }, 300)
}

function claimLeadership() {
    if (isLeader) return
    isLeader = true
    isLeaderRef.value = true
    connectSocket()
    if (broadcastChannel) {
        broadcastChannel.postMessage({ type: '__i_am_leader__' })
        broadcastChannel.postMessage({ type: '__request_topics__' })
        updateLeaderStatusBroadcast()
    }
}

function releaseLeadership() {
    isLeader = false
    isLeaderRef.value = false
    rtt.value = null
    if (wsClient) {
        wsClient.close()
        wsClient = null
    }
    if (leaderLockResolver) {
        leaderLockResolver()
        leaderLockResolver = null
    }
}

function processSingleEvent(data: any) {
    if (!data) return
    if (data.seq_id && typeof data.seq_id === 'number') {
        lastSeenSeqId = Math.max(lastSeenSeqId, data.seq_id)
    }

    if (data.type === 'ack' && data.ack_id && pendingAckCallbacks.has(data.ack_id)) {
        const pending = pendingAckCallbacks.get(data.ack_id)
        if (pending) {
            clearTimeout(pending.timer)
            pendingAckCallbacks.delete(data.ack_id)
            pending.resolve(data)
        }
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

    // Игнорируем служебные ping/pong в обработчиках событий
    if (data.type === 'ping' || data.type === 'pong') {
        return
    }

    // Если сокет сообщил о необходимости ресинхронизации из-за пропуска событий
    if (data.type === 'resync_required') {
        processSingleEvent({ type: 'ws_resync_required', message: data.message })
        return
    }

    // Если событие получено лидером напрямую с сокета, пересылаем ведомым вкладкам
    if (isFromDirectSocket && broadcastChannel && isLeader) {
        broadcastChannel.postMessage({ type: '__ws_event__', payload: data })
        updateLeaderStatusBroadcast()
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
        onPong: (currentRtt) => {
            rtt.value = currentRtt
            updateLeaderStatusBroadcast()
        },
        onOpen: () => {
            const isReconnect = wasDisconnected
            isConnected.value = true
            wasDisconnected = false

            updateLeaderStatusBroadcast()

            // Немедленная первичная калибровка RTT при подключении
            if (wsClient && wsClient.isConnected()) {
                wsClient.send('ping')
            }

            // Отправляем текущие подписки на топики серверу (включая топики от ведомых вкладок)
            activeTopics.forEach((_, topic) => {
                send({ type: 'subscribe', topic })
            })

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
            if (wsClient) {
                const currentRtt = wsClient.getRtt()
                if (currentRtt !== null) {
                    rtt.value = currentRtt
                    updateLeaderStatusBroadcast()
                }
            }
            processIncomingData(data, true)
        },
        onClose: () => {
            isConnected.value = false
            wasDisconnected = true
            rtt.value = null
            updateLeaderStatusBroadcast()
        },
        onError: () => {
            isConnected.value = false
            wasDisconnected = true
            rtt.value = null
            updateLeaderStatusBroadcast()
        },
        onAuthError: async () => {
            isConnected.value = false
            wasDisconnected = true
            rtt.value = null
            updateLeaderStatusBroadcast()
            const isValid = await ensureAuthStatus()
            if (!isValid) {
                clearAuthSession()
                if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
                    window.location.href = '/login'
                }
            } else {
                // ponytail: Токен успешно обновлен, перезапускаем WS клиент с новыми данными
                if (wsClient) {
                    wsClient.close()
                    wsClient = null
                }
                connectSocket()
            }
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

    if (eventType) {
        const count = (activeTopics.get(eventType) || 0) + 1
        activeTopics.set(eventType, count)
        if (count === 1) {
            send({ type: 'subscribe', topic: eventType })
        }
    }

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

        if (eventType) {
            const count = (activeTopics.get(eventType) || 0) - 1
            if (count <= 0) {
                activeTopics.delete(eventType)
                send({ type: 'unsubscribe', topic: eventType })
            } else {
                activeTopics.set(eventType, count)
            }
        }

        subscriberCount--
        if (subscriberCount <= 0) {
            subscriberCount = 0
            releaseLeadership()
        }
    }
}

/**
 * Send raw text or JSON object over WebSocket (with follower-to-leader proxying).
 */
export function send(data: string | object): boolean {
    if (wsClient) {
        wsClient.send(data)
        return true
    }
    // Если вызов отправки происходит на ведомой вкладке, проксируем вызов лидеру через BroadcastChannel
    if (!isLeader && broadcastChannel) {
        broadcastChannel.postMessage({ type: '__ws_send__', payload: data })
        return true
    }
    return false
}

/**
 * Send message with acknowledgment expectation (returns Promise resolving on ACK event).
 */
export function sendWithAck(payload: object, timeoutMs: number = 5000): Promise<any> {
    const ackId = `ack_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
    const msg = { ...payload, ack_id: ackId }

    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
            pendingAckCallbacks.delete(ackId)
            reject(new Error(`WebSocket ACK timeout for ack_id=${ackId}`))
        }, timeoutMs)

        pendingAckCallbacks.set(ackId, { resolve, reject, timer })

        const sent = send(msg)
        if (!sent) {
            clearTimeout(timer)
            pendingAckCallbacks.delete(ackId)
            reject(new Error('WebSocket is not connected and message could not be queued'))
        }
    })
}

/**
 * Explicitly trigger a heartbeat ping measurement (with follower-to-leader proxying).
 */
export function ping(): boolean {
    if (wsClient) {
        wsClient.ping()
        return true
    }
    if (!isLeader && broadcastChannel) {
        broadcastChannel.postMessage({ type: '__ws_ping__' })
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
            releaseLeadership()
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
        isLeader: isLeaderRef,
        activeTopicsCount: computed(() => activeTopics.size),
        lastEvent,
        rtt,
        connectionQuality,
        onEvent,
        subscribe,
        send,
        sendWithAck,
        ping,
    }
}

// Global API exposure for dynamic modules and widgets loaded at runtime
if (typeof window !== 'undefined') {
    const win = window as any
    win.NMS = win.NMS || {}
    win.NMS.events = {
        subscribe,
        send,
        sendWithAck,
        useWebSocket,
        isConnected,
        lastEvent,
        rtt,
        connectionQuality,
    }
}

