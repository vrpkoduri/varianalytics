/**
 * useSSE — reconnect behaviour tests.
 *
 * Verifies that the SSE hook:
 *  1. Creates an EventSource on mount when enabled
 *  2. Reconnects (close old + open new) when reconnectKey changes
 *  3. Does not create an EventSource when disabled
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSSE } from '../useSSE'

// ---- EventSource mock ----

class MockEventSource {
  static instances: MockEventSource[] = []

  url: string
  closed = false
  listeners: Record<string, Function[]> = {}
  onmessage: ((e: MessageEvent) => void) | null = null
  onerror: (() => void) | null = null

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  addEventListener(type: string, handler: Function) {
    if (!this.listeners[type]) this.listeners[type] = []
    this.listeners[type].push(handler)
  }

  removeEventListener() {}

  close() {
    this.closed = true
  }
}

beforeEach(() => {
  MockEventSource.instances = []
  ;(globalThis as any).EventSource = MockEventSource
})

afterEach(() => {
  delete (globalThis as any).EventSource
})

// ---- Tests ----

describe('useSSE', () => {
  it('creates EventSource on mount when enabled and conversationId provided', () => {
    const onEvent = vi.fn()

    renderHook(() => useSSE('conv-123', onEvent, true, 0))

    expect(MockEventSource.instances).toHaveLength(1)
    expect(MockEventSource.instances[0].url).toBe(
      '/api/gateway/chat/stream/conv-123',
    )
    expect(MockEventSource.instances[0].closed).toBe(false)
  })

  it('reconnects on reconnectKey change — closes old and opens new EventSource', () => {
    const onEvent = vi.fn()

    const { rerender } = renderHook(
      ({ reconnectKey }) => useSSE('conv-123', onEvent, true, reconnectKey),
      { initialProps: { reconnectKey: 0 } },
    )

    expect(MockEventSource.instances).toHaveLength(1)
    const firstES = MockEventSource.instances[0]

    // Change reconnectKey to trigger reconnect
    rerender({ reconnectKey: 1 })

    // Old EventSource should be closed
    expect(firstES.closed).toBe(true)
    // New EventSource should be created
    expect(MockEventSource.instances).toHaveLength(2)
    expect(MockEventSource.instances[1].closed).toBe(false)
  })

  it('does not create EventSource when disabled', () => {
    const onEvent = vi.fn()

    renderHook(() => useSSE('conv-123', onEvent, false, 0))

    expect(MockEventSource.instances).toHaveLength(0)
  })
})
