import { useState, useEffect, useCallback, useMemo } from 'react'
import { api } from '@/utils/api'
import { useFilterParams } from '@/hooks/useFilterParams'
import { buildFilterQuery } from '@/utils/filterParams'
import { transformVariances } from '@/utils/transformers'
import { MOCK_VARIANCES } from '@/mocks/dashboardData'

export function useVariances(filters?: { plCategory?: string; buId?: string; ignoreGlobalBU?: boolean }) {
  const { params } = useFilterParams()

  const [variances, setVariances] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [usingMock, setUsingMock] = useState(false)

  // Build query with special bu_id handling:
  // - ignoreGlobalBU: strip the global bu_id, use only filters.buId if provided
  // - otherwise: filters.buId overrides global bu_id
  const query = useMemo(() => {
    const adjusted = { ...params }
    if (filters?.ignoreGlobalBU) {
      adjusted.bu_id = filters?.buId || undefined
    } else if (filters?.buId) {
      adjusted.bu_id = filters.buId
    }
    return buildFilterQuery(adjusted, {
      page,
      page_size: 50,
      pl_category: filters?.plCategory,
    })
  }, [params, page, filters?.plCategory, filters?.buId, filters?.ignoreGlobalBU])

  useEffect(() => {
    setLoading(true)

    api.computation
      .get(`/variances/${query}`)
      .then((data: any) => {
        const rawItems = data.variances || data.items || []
        if (rawItems.length > 0) {
          setVariances(transformVariances(rawItems))
          setTotal(data.total || data.totalCount || rawItems.length)
          setUsingMock(false)
        } else {
          // Empty API response — fall back to mock data
          setVariances(MOCK_VARIANCES)
          setTotal(MOCK_VARIANCES.length)
          setUsingMock(true)
        }
        setLoading(false)
      })
      .catch(() => {
        setVariances(MOCK_VARIANCES)
        setTotal(MOCK_VARIANCES.length)
        setUsingMock(true)
        setLoading(false)
      })
  }, [query])

  const fetchVarianceDetail = useCallback(async (varianceId: string) => {
    try {
      return await api.computation.get(`/variances/${varianceId}`)
    } catch {
      return null
    }
  }, [])

  return { variances, total, page, setPage, loading, usingMock, fetchVarianceDetail }
}
