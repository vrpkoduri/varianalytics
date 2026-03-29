import { useState, useEffect } from 'react';
import type { ReviewQueueItem } from '@/types/api';

interface UseReviewQueueResult {
  items: ReviewQueueItem[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Custom hook for fetching and managing the review queue.
 */
export function useReviewQueue(): UseReviewQueueResult {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState(0);

  const refetch = () => setFetchTrigger((prev) => prev + 1);

  useEffect(() => {
    // TODO: Implement API call to gateway service
    // GET /api/gateway/review/queue
    setIsLoading(false);
    setItems([]);
    setError(null);

    void fetchTrigger;
  }, [fetchTrigger]);

  return { items, isLoading, error, refetch };
}
