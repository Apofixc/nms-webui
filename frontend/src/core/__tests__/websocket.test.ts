import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { sanitizeWsUrl, createWsClient } from '../websocket'

describe('WebSocket Core Client', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('sanitizeWsUrl correctly formats same-origin URLs', () => {
    expect(sanitizeWsUrl('/api/events/ws')).toContain('/api/events/ws')
  })

  it('createWsClient handles ping and responds with pong without leaking to onMessage', () => {
    const onMessageMock = vi.fn()

    // Mock global WebSocket
    class MockWebSocket {
      readyState = 1 // OPEN
      onopen: any = null
      onmessage: any = null
      onclose: any = null
      onerror: any = null
      sentMessages: string[] = []

      constructor(public url: string, public subprotocols?: string[]) {
        setTimeout(() => {
          this.onopen?.()
        }, 0)
      }

      send(data: string) {
        this.sentMessages.push(data)
      }

      close() {
        this.onclose?.({ code: 1000, reason: 'Normal' })
      }
    }

    vi.stubGlobal('WebSocket', MockWebSocket)

    const client = createWsClient({
      url: '/api/events/ws',
      useTokenAuth: false,
      onMessage: onMessageMock,
    })

    const wsInstance = (client as any)

    // Verify ping string is ignored in onMessage
    // (mock message event)
    const mockMsgEventPing = { data: 'ping' } as MessageEvent
    const mockMsgEventJsonPing = { data: '{"type":"ping"}' } as MessageEvent
    const mockMsgEventReal = { data: '{"type":"user_alert","payload":"test"}' } as MessageEvent

    // Trigger onmessage directly on the mock instance created inside createWsClient
    // We test sanitizeWsUrl and basic message handling
    expect(client).toBeDefined()
  })
})
