import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { sanitizeWsUrl, createWsClient } from '../websocket'

describe('WebSocket Core Client', () => {
  let createdSockets: any[] = []

  class MockWebSocket {
    readyState = 1 // OPEN
    onopen: any = null
    onmessage: any = null
    onclose: any = null
    onerror: any = null
    sentMessages: string[] = []

    constructor(public url: string, public subprotocols?: string[]) {
      createdSockets.push(this)
      setTimeout(() => {
        this.onopen?.()
      }, 0)
    }

    send(data: string) {
      this.sentMessages.push(data)
    }

    close(code: number = 1000, reason?: string) {
      this.readyState = 3 // CLOSED
      this.onclose?.({ code, reason })
    }
  }

  beforeEach(() => {
    createdSockets = []
    vi.useFakeTimers()
    vi.stubGlobal('WebSocket', MockWebSocket)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('sanitizeWsUrl correctly formats same-origin URLs', () => {
    expect(sanitizeWsUrl('/api/events/ws')).toContain('/api/events/ws')
  })

  it('createWsClient filters raw ping/pong strings without triggering onMessage', async () => {
    const onMessageMock = vi.fn()

    const client = createWsClient({
      url: '/api/events/ws',
      useTokenAuth: false,
      onMessage: onMessageMock,
    })

    await vi.advanceTimersByTimeAsync(10)
    const wsInstance = createdSockets[0]
    expect(wsInstance).toBeDefined()

    // Send raw ping
    wsInstance.onmessage?.({ data: 'ping' } as MessageEvent)
    expect(onMessageMock).not.toHaveBeenCalled()
    expect(wsInstance.sentMessages).toContain('{"type":"pong"}')

    // Send raw pong
    wsInstance.onmessage?.({ data: 'pong' } as MessageEvent)
    expect(onMessageMock).not.toHaveBeenCalled()

    // Send valid JSON event
    wsInstance.onmessage?.({ data: '{"type":"alert","msg":"hello"}' } as MessageEvent)
    expect(onMessageMock).toHaveBeenCalledWith({ type: 'alert', msg: 'hello' }, expect.any(Object))

    client.close()
  })
})

