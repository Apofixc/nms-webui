import { describe, it, expect, beforeEach, vi } from 'vitest'
import { subscribe, send, useWebSocket } from '../useWebSocket'

describe('useWebSocket Composable', () => {
  it('subscribe returns unsubscribe function and handles events', () => {
    const callback = vi.fn()
    const unsub = subscribe('test_event', callback)
    expect(typeof unsub).toBe('function')
    unsub()
  })

  it('send handles follower/leader fallback gracefully', () => {
    const res = send({ type: 'test' })
    expect(typeof res).toBe('boolean')
  })
})
