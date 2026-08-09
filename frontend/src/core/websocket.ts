/**
 * Единая клиентская утилита для безопасной работы с WebSocket.
 * 
 * Особенности:
 * - Передача JWT-токена через Sec-WebSocket-Protocol ['bearer', token]
 * - Защита Same-Origin: разрешение подсоединений только к текущему хосту
 * - Автоматический reconnect с экспоненциальной задержкой (Exponential Backoff)
 * - Автоматическая фильтрация и генерация PONG на серверный PING
 * - Обработка кодов закрытия (1008 Policy/Auth Error)
 */
import { getStoredToken, ensureAuthStatus, clearAuthSession } from '@/core/auth'
import { apiGetWsTicket } from '@/core/api'

export type ConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected'
export type WsProtocolFormat = 'json' | 'msgpack'

export interface WsClientOptions {
  url: string
  onMessage?: (data: any, rawEvent: MessageEvent) => void
  onOpen?: () => void
  onClose?: (event: CloseEvent) => void
  onError?: (event: Event) => void
  onAuthError?: (event: CloseEvent) => void
  onPong?: (rttMs: number) => void
  onStateChange?: (state: ConnectionState, attempt: number) => void
  autoReconnect?: boolean
  maxReconnectAttempts?: number
  heartbeatIntervalMs?: number
  connectionTimeoutMs?: number
  useTokenAuth?: boolean
  protocolFormat?: WsProtocolFormat

  maxQueueSize?: number
}

export interface WsClient {
  send: (data: string | object) => void
  ping: () => void
  close: (code?: number, reason?: string) => void
  isConnected: () => boolean
  getState: () => ConnectionState
  getReconnectAttempts: () => number
  getQueueLength: () => number
  clearQueue: () => void
  getRtt: () => number | null
}

export function sanitizeWsUrl(endpoint: string): string {
  if (typeof window === 'undefined') return endpoint

  if (!endpoint.startsWith('/') && !endpoint.includes('://')) {
    endpoint = '/' + endpoint
  }

  const currentHost = window.location.host
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'

  if (endpoint.startsWith('/')) {
    return `${protocol}//${currentHost}${endpoint}`
  }

  try {
    const parsed = new URL(endpoint.replace(/^ws/, 'http'))
    // ponytail: Блокируем подключение к чужим доменам для предотвращения утечки данных (Same-Origin restriction)
    if (parsed.host !== currentHost) {
      console.warn(`[WsClient] Blocked cross-origin WS attempt to ${parsed.host}. Falling back to same-origin.`)
      return `${protocol}//${currentHost}${parsed.pathname}${parsed.search}`
    }
    return endpoint.startsWith('http')
      ? endpoint.replace(/^http/, 'ws')
      : endpoint
  } catch {
    return `${protocol}//${currentHost}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`
  }
}

export function createWsClient(options: WsClientOptions): WsClient {
  const {
    url: rawUrl,
    onMessage,
    onOpen,
    onClose,
    onError,
    onAuthError,
    onPong,
    onStateChange,
    autoReconnect = true,
    maxReconnectAttempts = 10,
    heartbeatIntervalMs = 30000,
    connectionTimeoutMs = 10000,
    useTokenAuth = true,
    protocolFormat = 'json',
    maxQueueSize = 100,
  } = options

  let socket: WebSocket | null = null
  let isExplicitlyClosed = false
  let reconnectAttempts = 0
  let connectionState: ConnectionState = 'disconnected'
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let resetAttemptsTimer: ReturnType<typeof setTimeout> | null = null
  let connectTimeoutTimer: ReturnType<typeof setTimeout> | null = null
  const sendQueue: string[] = []

  let isConnecting = false
  let lastPingTimestamp: number | null = null
  let currentRttMs: number | null = null
  let pongTimeoutTimer: ReturnType<typeof setTimeout> | null = null

  const targetUrl = sanitizeWsUrl(rawUrl)

  function setState(newState: ConnectionState) {
    if (connectionState !== newState) {
      connectionState = newState
      onStateChange?.(connectionState, reconnectAttempts)
    }
  }

  function flushQueue() {
    while (sendQueue.length > 0 && socket && socket.readyState === WebSocket.OPEN) {
      const payload = sendQueue.shift()
      if (payload) {
        try {
          socket.send(payload)
        } catch (err) {
          console.warn('[WsClient] Failed to send queued message:', err)
        }
      }
    }
  }

  function handleOnline() {
    if (!isExplicitlyClosed && autoReconnect && (!socket || (socket.readyState !== WebSocket.OPEN && socket.readyState !== WebSocket.CONNECTING))) {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      connect()
    } else if (socket && socket.readyState === WebSocket.OPEN) {
      sendPing()
    }
  }

  function handleVisibilityChange() {
    if (typeof document === 'undefined') return
    if (document.visibilityState === 'visible' && !isExplicitlyClosed && autoReconnect) {
      if (!socket || (socket.readyState !== WebSocket.OPEN && socket.readyState !== WebSocket.CONNECTING)) {
        if (reconnectTimer) clearTimeout(reconnectTimer)
        connect()
      } else if (socket.readyState === WebSocket.OPEN) {
        sendPing()
      }
    }
  }

  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    window.addEventListener('online', handleOnline)
    document.addEventListener('visibilitychange', handleVisibilityChange)
  }

  function sendPing() {
    if (socket && socket.readyState === WebSocket.OPEN) {
      try {
        lastPingTimestamp = typeof performance !== 'undefined' ? performance.now() : Date.now()
        socket.send('ping')
        if (pongTimeoutTimer) clearTimeout(pongTimeoutTimer)
        pongTimeoutTimer = setTimeout(() => {
          console.warn('[WsClient] Heartbeat pong timeout (server unresponsive). Force closing socket.')
          try {
            socket?.close(1001, 'Heartbeat Pong Timeout')
          } catch {}
        }, 10000)
      } catch {}
    }
  }

  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = setInterval(sendPing, heartbeatIntervalMs)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
    if (pongTimeoutTimer) {
      clearTimeout(pongTimeoutTimer)
      pongTimeoutTimer = null
    }
    if (connectTimeoutTimer) {
      clearTimeout(connectTimeoutTimer)
      connectTimeoutTimer = null
    }
  }

  function handlePongReceived() {
    if (pongTimeoutTimer) {
      clearTimeout(pongTimeoutTimer)
      pongTimeoutTimer = null
    }
    if (lastPingTimestamp !== null) {
      const now = typeof performance !== 'undefined' ? performance.now() : Date.now()
      const rawRtt = Math.max(0, Math.round(now - lastPingTimestamp))
      lastPingTimestamp = null
      currentRttMs = currentRttMs === null ? rawRtt : Math.round(0.3 * rawRtt + 0.7 * currentRttMs)
      if (currentRttMs !== null) {
        onPong?.(currentRttMs)
      }
    }
  }

  function scheduleReconnect() {
    if (!isExplicitlyClosed && autoReconnect && reconnectAttempts < maxReconnectAttempts) {
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 15000) + Math.random() * 500
      reconnectAttempts++
      setState('reconnecting')
      reconnectTimer = setTimeout(() => {
        connect()
      }, delay)
    } else if (reconnectAttempts >= maxReconnectAttempts) {
      setState('disconnected')
    }
  }

  async function connect() {
    if (isExplicitlyClosed || isConnecting) return
    isConnecting = true

    if (reconnectAttempts > 0) {
      setState('reconnecting')
    } else {
      setState('connecting')
    }

    // ponytail: Предварительная отвязка обработчиков и закрытие существующего сокета во избежание утечек и гонки
    if (socket) {
      try {
        socket.onopen = null
        socket.onmessage = null
        socket.onerror = null
        socket.onclose = null
        if (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN) {
          socket.close()
        }
      } catch {}
      socket = null
    }

    try {
      const subprotocols: string[] = []
      if (useTokenAuth) {
        const token = getStoredToken()
        if (token && token !== 'system_disabled_auth') {
          try {
            const ticket = await apiGetWsTicket()
            if (ticket) {
              subprotocols.push('bearer', ticket)
            } else if (token) {
              subprotocols.push('bearer', token)
            }
          } catch (err) {
            console.warn('[WsClient] Failed to fetch WS ticket, falling back to stored token:', err)
            if (token) {
              subprotocols.push('bearer', token)
            }
          }
        }
      }

      if (isExplicitlyClosed) return

      if (connectTimeoutTimer) clearTimeout(connectTimeoutTimer)
      connectTimeoutTimer = setTimeout(() => {
        if (socket && socket.readyState === WebSocket.CONNECTING) {
          console.warn('[WsClient] Connection attempt timed out. Closing socket.')
          try {
            socket.close(1006, 'Connection Timeout')
          } catch {}
        }
      }, connectionTimeoutMs)

      socket = subprotocols.length > 0 ? new WebSocket(targetUrl, subprotocols) : new WebSocket(targetUrl)

      socket.onopen = () => {
        if (connectTimeoutTimer) {
          clearTimeout(connectTimeoutTimer)
          connectTimeoutTimer = null
        }
        if (resetAttemptsTimer) clearTimeout(resetAttemptsTimer)
        resetAttemptsTimer = setTimeout(() => {
          reconnectAttempts = 0
        }, 5000)
        setState('connected')
        startHeartbeat()
        flushQueue()
        onOpen?.()
      }

      socket.onmessage = (event) => {
        if (event.data === 'ping') {
          try {
            socket?.send(JSON.stringify({ type: 'pong' }))
          } catch {}
          return
        }
        if (event.data === 'pong' || event.data === '{"type":"pong"}') {
          handlePongReceived()
          return
        }

        if (typeof event.data === 'string') {
          const trimmed = event.data.trim()
          if (trimmed === 'ping' || trimmed === 'pong') {
            if (trimmed === 'pong') handlePongReceived()
            return
          }
        }

        try {
          const parsed = JSON.parse(event.data)
          if (parsed && parsed.type === 'ping') {
            try {
              socket?.send(JSON.stringify({ type: 'pong' }))
            } catch {}
            return
          }
          if (parsed && parsed.type === 'pong') {
            handlePongReceived()
            return
          }
          onMessage?.(parsed, event)
        } catch {
          onMessage?.(event.data, event)
        }
      }

      socket.onerror = (event) => {
        onError?.(event)
      }

      socket.onclose = (event) => {
        if (connectTimeoutTimer) {
          clearTimeout(connectTimeoutTimer)
          connectTimeoutTimer = null
        }
        stopHeartbeat()

        if (resetAttemptsTimer) clearTimeout(resetAttemptsTimer)
        setState('disconnected')
        onClose?.(event)

        if (event.code === 4008) {
          console.warn('[WsClient] Connection closed: Too many active connections (4008)')
          scheduleReconnect()
          return
        }

        if (event.code === 4029) {
          console.warn('[WsClient] Connection closed: Rate limit exceeded (4029)')
          scheduleReconnect()
          return
        }

        if (event.code === 1008) {
          console.warn('[WsClient] Connection closed with 1008 (Auth/Policy Error)')
          if (onAuthError) {
            onAuthError(event)
          } else {
            ensureAuthStatus().then((isValid) => {
              if (!isValid) {
                clearAuthSession()
                if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
                  window.location.href = '/login'
                }
              }
            })
          }
          return
        }

        scheduleReconnect()
      }
    } catch (err) {
      console.error('[WsClient] Connection init error:', err)
      setState('disconnected')
      scheduleReconnect()
    } finally {
      isConnecting = false
    }
  }

  connect()

  return {
    send(data: string | object) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data)
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(payload)
      } else if (!isExplicitlyClosed) {
        if (sendQueue.length >= maxQueueSize) {
          const dropped = sendQueue.shift()
          console.warn(`[WsClient] Send queue limit reached (${maxQueueSize}). Dropped oldest message:`, dropped)
        }
        sendQueue.push(payload)
      }
    },
    ping() {
      sendPing()
    },
    close(code: number = 1000, reason: string = 'Normal Closure') {
      isExplicitlyClosed = true
      sendQueue.length = 0
      stopHeartbeat()
      setState('disconnected')
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (resetAttemptsTimer) clearTimeout(resetAttemptsTimer)
      if (connectTimeoutTimer) clearTimeout(connectTimeoutTimer)

      if (typeof window !== 'undefined' && typeof document !== 'undefined') {
        window.removeEventListener('online', handleOnline)
        document.removeEventListener('visibilitychange', handleVisibilityChange)
      }
      if (socket) {
        try {
          socket.onopen = null
          socket.onmessage = null
          socket.onerror = null
          socket.onclose = null
          socket.close(code, reason)
        } catch {}
        socket = null
      }
    },
    isConnected() {
      return socket !== null && socket.readyState === WebSocket.OPEN
    },
    getState() {
      return connectionState
    },
    getReconnectAttempts() {
      return reconnectAttempts
    },
    getQueueLength() {
      return sendQueue.length
    },
    clearQueue() {
      sendQueue.length = 0
    },
    getRtt() {
      return currentRttMs
    },
  }
}


