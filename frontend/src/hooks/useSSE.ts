import { useCallback, useEffect, useRef, useState } from 'react';
import type { SSEEvent } from '@/types/api';

interface UseSSEOptions {
  url: string;
  enabled?: boolean;
  onEvent?: (event: SSEEvent) => void;
  onError?: (error: Event) => void;
}

interface UseSSEResult {
  isConnected: boolean;
  lastEvent: SSEEvent | null;
  error: Event | null;
  connect: () => void;
  disconnect: () => void;
}

/**
 * Custom hook for managing a Server-Sent Events (SSE) streaming connection.
 * Used for chat streaming and real-time updates.
 */
export function useSSE({
  url,
  enabled = false,
  onEvent,
  onError,
}: UseSSEOptions): UseSSEResult {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [error, setError] = useState<Event | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  const connect = useCallback(() => {
    disconnect();

    // TODO: Implement SSE connection to gateway service
    // const source = new EventSource(url);
    // source.onopen = () => setIsConnected(true);
    // source.onmessage = (e) => { ... };
    // source.onerror = (e) => { ... };
    // eventSourceRef.current = source;

    void url;
    void onEvent;
    void onError;
  }, [url, onEvent, onError, disconnect]);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => disconnect();
  }, [enabled, connect, disconnect]);

  return { isConnected, lastEvent, error, connect, disconnect };
}
