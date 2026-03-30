import { useEffect, useRef, useCallback } from 'react'

export interface SSEEvent {
  type: string
  payload: any
}

export function useSSE(
  conversationId: string | null,
  onEvent: (event: SSEEvent) => void,
  enabled: boolean = true,
) {
  const esRef = useRef<EventSource | null>(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    if (!conversationId || !enabled) return

    const url = `/api/gateway/chat/stream/${conversationId}`
    const es = new EventSource(url)
    esRef.current = es

    // Listen for typed events
    const eventTypes = [
      'token',
      'data_table',
      'mini_chart',
      'suggestion',
      'confidence',
      'netting_alert',
      'review_status',
      'done',
      'error',
    ]

    for (const type of eventTypes) {
      es.addEventListener(type, (e: MessageEvent) => {
        try {
          const payload = JSON.parse(e.data)
          onEventRef.current({ type, payload })
          if (type === 'done' || type === 'error') {
            es.close()
          }
        } catch {
          // Ignore malformed JSON
        }
      })
    }

    // Generic message handler as fallback
    es.onmessage = (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data)
        onEventRef.current({ type: payload.type || 'token', payload })
      } catch {
        // Ignore malformed JSON
      }
    }

    es.onerror = () => {
      onEventRef.current({ type: 'error', payload: { message: 'Connection lost' } })
      es.close()
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [conversationId, enabled])

  const close = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  return { close }
}
