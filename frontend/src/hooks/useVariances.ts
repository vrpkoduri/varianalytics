import { useState, useEffect, useCallback } from 'react'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { api, buildParams } from '@/utils/api'
import { transformVariances } from '@/utils/transformers'
import { MOCK_VARIANCES } from '@/mocks/dashboardData'

export function useVariances(filters?: { plCategory?: string; buId?: string }) {
  const { filters: globalFilters } = useGlobalFilters()
  const { viewType, comparisonBase } = globalFilters
  const period = globalFilters.period ? `${globalFilters.period.year}-${String(globalFilters.period.month).padStart(2, '0')}` : '2026-06'

  const [variances, setVariances] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [usingMock, setUsingMock] = useState(false)

  useEffect(() => {
    setLoading(true)
    const params = buildParams({
      period_id: period,
      view_id: viewType,
      base_id: comparisonBase,
      page: page,
      page_size: 50,
      pl_category: filters?.plCategory,
      bu_id: filters?.buId,
    })

    api.computation
      .get(`/variances/${params}`)
      .then((data: any) => {
        const rawItems = data.variances || data.items || []
        setVariances(transformVariances(rawItems))
        setTotal(data.total || data.totalCount || rawItems.length)
        setUsingMock(false)
        setLoading(false)
      })
      .catch(() => {
        setVariances(MOCK_VARIANCES)
        setTotal(MOCK_VARIANCES.length)
        setUsingMock(true)
        setLoading(false)
      })
  }, [viewType, comparisonBase, period, page, filters?.plCategory, filters?.buId])

  const fetchVarianceDetail = useCallback(async (varianceId: string) => {
    try {
      return await api.computation.get(`/variances/${varianceId}`)
    } catch {
      return null
    }
  }, [])

  return { variances, total, page, setPage, loading, usingMock, fetchVarianceDetail }
}
