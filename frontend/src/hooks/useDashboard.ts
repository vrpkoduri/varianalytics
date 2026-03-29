import { useState, useEffect } from 'react';
import type { DashboardData } from '@/types/api';
import { useGlobalFilters } from '@/context/GlobalFiltersContext';

interface UseDashboardResult {
  data: DashboardData | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Custom hook for fetching dashboard summary data.
 */
export function useDashboard(): UseDashboardResult {
  const { filters } = useGlobalFilters();
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState(0);

  const refetch = () => setFetchTrigger((prev) => prev + 1);

  useEffect(() => {
    // TODO: Implement API call to computation service
    // GET /api/computation/dashboard?period=...&bu=...&view=...&base=...
    setIsLoading(false);
    setData(null);
    setError(null);

    void filters;
    void fetchTrigger;
  }, [filters, fetchTrigger]);

  return { data, isLoading, error, refetch };
}
