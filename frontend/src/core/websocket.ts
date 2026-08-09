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

export interface WsClientOptions {
  url: string
  onMessage?: (data: any, rawEvent: MessageEvent) => void
  onOpen?: () => void
  onClose?: (event: CloseEvent) => void
  onError?: (event: Event) => void
  onAuthError?: (event: CloseEvent) => void
  autoReconnect?: boolean
  maxReconnectAttempts?: number
  heartbeatIntervalMs?: number
  useTokenAuth?: boolean
}

export interface WsClient {
  send: (data: string | object) => void
  close: (code?: number, reason?: string) => void
  isConnected: () => boolean
}

export function sanitizeWsUrl(endpoint: string): string {
  if (typeof window === 'undefined') return endpoint

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
    autoReconnect = true,
    maxReconnectAttempts = 10,
    heartbeatIntervalMs = 30000,
    useTokenAuth = true,
  } = options

  let socket: WebSocket | null = null
  let isExplicitlyClosed = false
  let reconnectAttempts = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let resetAttemptsTimer: ReturnType<typeof setTimeout> | null = null

  const targetUrl = sanitizeWsUrl(rawUrl)

  function handleOnline() {
    if (!isExplicitlyClosed && autoReconnect && (!socket || socket.readyState !== WebSocket.OPEN)) {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      connect()
    }
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('online', handleOnline)
  }

  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = setInterval(() => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        try {
          socket.send('ping')
        } catch {}
      }
    }, heartbeatIntervalMs)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  function scheduleReconnect() {
    if (!isExplicitlyClosed && autoReconnect && reconnectAttempts < maxReconnectAttempts) {
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 15000) + Math.random() * 500
      reconnectAttempts++
      reconnectTimer = setTimeout(() => {
        connect()
      }, delay)
    }
  }

  async function connect() {
    if (isExplicitlyClosed) return

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

      socket = subprotocols.length > 0 ? new WebSocket(targetUrl, subprotocols) : new WebSocket(targetUrl)

      socket.onopen = () => {
        if (resetAttemptsTimer) clearTimeout(resetAttemptsTimer)
        resetAttemptsTimer = setTimeout(() => {
          reconnectAttempts = 0
        }, 5000)
        startHeartbeat()
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
          return
        }

        if (typeof event.data === 'string') {
          const trimmed = event.data.trim()
          if (trimmed === 'ping' || trimmed === 'pong') return
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
        stopHeartbeat()
        if (resetAttemptsTimer) clearTimeout(resetAttemptsTimer)
        onClose?.(event)

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
      scheduleReconnect()
    }
  }

  connect()

  return {
    send(data: string | object) {
      if (socket && socket.readyState === WebSocket.OPEN) {
        const payload = typeof data === 'string' ? data : JSON.stringify(data)
        socket.send(payload)
      }
    },
    close(code: number = 1000, reason: string = 'Normal Closure') {
      isExplicitlyClosed = true
      stopHeartbeat()
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (resetAttemptsTimer) clearTimeout(resetAttemptsTimer)
      if (typeof window !== 'undefined') {
        window.removeEventListener('online', handleOnline)
      }
      if (socket) {
        socket.close(code, reason)
        socket = null
      }
    },
    isConnected() {
      return socket !== null && socket.readyState === WebSocket.OPEN
    },
  }
}

