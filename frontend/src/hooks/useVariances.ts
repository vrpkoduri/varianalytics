import { useState, useEffect } from 'react';
import type { VarianceSummary } from '@/types/api';
import { useGlobalFilters } from '@/context/GlobalFiltersContext';

interface UseVariancesResult {
  variances: VarianceSummary[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Custom hook for fetching variance data from the computation service.
 * Reacts to global filter changes.
 */
export function useVariances(): UseVariancesResult {
  const { filters } = useGlobalFilters();
  const [variances, setVariances] = useState<VarianceSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState(0);

  const refetch = () => setFetchTrigger((prev) => prev + 1);

  useEffect(() => {
    // TODO: Implement API call to computation service
    // GET /api/computation/variances?period=...&bu=...&view=...&base=...
    setIsLoading(false);
    setVariances([]);
    setError(null);

    // Placeholder to suppress unused variable warnings in strict mode
    void filters;
    void fetchTrigger;
  }, [filters, fetchTrigger]);

  return { variances, isLoading, error, refetch };
}
