/**
 * Unified filter parameters hook.
 *
 * THE canonical source of filter params for ALL data-fetching hooks.
 * Reads from GlobalFiltersContext + UserContext and returns a consistent
 * FilterParams object. Any filter change triggers re-renders of all
 * hooks that depend on this, ensuring all sections update in tandem.
 *
 * Usage:
 *   const { params, query } = useFilterParams()
 *   api.computation.get(`/dashboard/summary${query}`)
 */
import { useMemo } from 'react'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { useUser } from '@/context/UserContext'
import { type FilterParams, buildFilterQuery } from '@/utils/filterParams'

interface UseFilterParamsResult {
  /** Structured filter params object */
  params: FilterParams
  /** Pre-built query string for API calls (starts with "?") */
  query: string
  /** Build a query string with extra params beyond the standard filters */
  buildQuery: (extras?: Record<string, string | number | undefined>) => string
  /** The raw period string (YYYY-MM) */
  period: string
}

export function useFilterParams(): UseFilterParamsResult {
  const { filters } = useGlobalFilters()
  const { persona } = useUser()

  const period = filters.period
    ? `${filters.period.year}-${String(filters.period.month).padStart(2, '0')}`
    : '2026-06'

  const params: FilterParams = useMemo(() => {
    const p: FilterParams = {
      period_id: period,
      view_id: filters.viewType,
      base_id: filters.comparisonBase,
      persona,
    }

    // Business unit
    if (filters.businessUnit) {
      p.bu_id = filters.businessUnit
    }

    // Dimension filter — map to the correct param name
    if (filters.dimensionFilter) {
      const { dimension, nodeId } = filters.dimensionFilter
      switch (dimension) {
        case 'geography':
          p.geo_node_id = nodeId
          break
        case 'segment':
          p.segment_node_id = nodeId
          break
        case 'lob':
          p.lob_node_id = nodeId
          break
        case 'costcenter':
          p.costcenter_node_id = nodeId
          break
      }
    }

    return p
  }, [period, filters.viewType, filters.comparisonBase, filters.businessUnit, filters.dimensionFilter, persona])

  const query = useMemo(() => buildFilterQuery(params), [params])

  const buildQuery = useMemo(
    () => (extras?: Record<string, string | number | undefined>) => buildFilterQuery(params, extras),
    [params],
  )

  return { params, query, buildQuery, period }
}
