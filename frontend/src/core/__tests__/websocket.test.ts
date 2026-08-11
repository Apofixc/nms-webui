import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { sanitizeWsUrl, createWsClient } from '../websocket'

describe('WebSocket Core Client', () => {
  let createdSockets: any[] = []

  class MockWebSocket {
    static CONNECTING = 0
    static OPEN = 1
    static CLOSING = 2
    static CLOSED = 3

    readyState = 0 // CONNECTING
    onopen: any = null
    onmessage: any = null
    onclose: any = null
    onerror: any = null
    sentMessages: string[] = []

    constructor(public url: string, public subprotocols?: string[]) {
      createdSockets.push(this)
      setTimeout(() => {
        if (this.readyState === MockWebSocket.CONNECTING) {
          this.readyState = MockWebSocket.OPEN
          this.onopen?.()
        }
      }, 10)
    }

    send(data: string) {
      this.sentMessages.push(data)
    }

    close(code: number = 1000, reason?: string) {
      this.readyState = MockWebSocket.CLOSED
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

    await vi.advanceTimersByTimeAsync(20)
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

  it('buffers send calls while socket is CONNECTING and flushes on onopen', async () => {
    const client = createWsClient({
      url: '/api/events/ws',
      useTokenAuth: false,
    })

    expect(client.isConnected()).toBe(false)

    // Send messages before connection is OPEN
    client.send({ type: 'subscribe', topic: 'devices' })
    client.send({ type: 'subscribe', topic: 'alerts' })

    expect(client.getQueueLength()).toBe(2)

    // Advance time to trigger onopen
    await vi.advanceTimersByTimeAsync(20)

    const wsInstance = createdSockets[0]
    expect(client.isConnected()).toBe(true)
    expect(client.getQueueLength()).toBe(0)
    expect(wsInstance.sentMessages).toEqual([
      '{"type":"subscribe","topic":"devices"}',
      '{"type":"subscribe","topic":"alerts"}',
    ])

    client.close()
  })

  it('respects maxQueueSize limit and discards oldest messages (FIFO)', async () => {
    const client = createWsClient({
      url: '/api/events/ws',
      useTokenAuth: false,
      maxQueueSize: 2,
    })

    client.send('msg1')
    client.send('msg2')
    client.send('msg3') // msg1 should be dropped

    expect(client.getQueueLength()).toBe(2)

    await vi.advanceTimersByTimeAsync(20)
    const wsInstance = createdSockets[0]

    expect(wsInstance.sentMessages).toEqual(['msg2', 'msg3'])

    client.close()
  })

  it('clears queue when close() is called', () => {
    const client = createWsClient({
      url: '/api/events/ws',
      useTokenAuth: false,
    })

    client.send('msg1')
    expect(client.getQueueLength()).toBe(1)

    client.close()
    expect(client.getQueueLength()).toBe(0)
  })

  it('calculates RTT correctly when heartbeat ping and pong are exchanged', async () => {
    const client = createWsClient({
      url: '/api/events/ws',
      useTokenAuth: false,
      heartbeatIntervalMs: 1000,
    })

    await vi.advanceTimersByTimeAsync(20)
    const wsInstance = createdSockets[0]

    expect(client.getRtt()).toBeNull()

    // Trigger heartbeat ping
    await vi.advanceTimersByTimeAsync(1000)
    expect(wsInstance.sentMessages).toContain('ping')

    // Simulate pong response after 45ms
    await vi.advanceTimersByTimeAsync(45)
    wsInstance.onmessage?.({ data: 'pong' } as MessageEvent)

    expect(client.getRtt()).toBeGreaterThanOrEqual(0)

    client.close()
  })

  it('does not trigger onAuthError when socket closes with code 4008', async () => {
    const onAuthErrorMock = vi.fn()
    const onCloseMock = vi.fn()

    const client = createWsClient({
      url: '/api/events/ws',
      useTokenAuth: false,
      onAuthError: onAuthErrorMock,
      onClose: onCloseMock,
    })

    await vi.advanceTimersByTimeAsync(20)
    const wsInstance = createdSockets[0]

    wsInstance.onclose?.({ code: 4008, reason: 'Too many active connections' } as CloseEvent)

    expect(onCloseMock).toHaveBeenCalled()
    expect(onAuthErrorMock).not.toHaveBeenCalled()

    client.close()
  })

  it('supports msgpack protocolFormat option', async () => {
    const client = createWsClient({
      url: '/api/events/ws',
      useTokenAuth: false,
      protocolFormat: 'msgpack',
    })

    await vi.advanceTimersByTimeAsync(20)
    const wsInstance = createdSockets[0]
    expect(wsInstance.url).toContain('protocol=msgpack')

    client.close()
  })

  it('aborts connection attempt if useTokenAuth is true and no token exists', async () => {
    const client = createWsClient({
      url: '/api/events/ws',
      useTokenAuth: true,
    })

    await vi.advanceTimersByTimeAsync(20)
    expect(createdSockets.length).toBe(0)
    expect(client.getState()).toBe('disconnected')
  })
})


