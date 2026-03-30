import { useState, useEffect } from 'react'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { api, buildParams } from '@/utils/api'
import { transformPLRows } from '@/utils/transformers'
import { MOCK_PL_DATA, MOCK_MARGINS } from '@/mocks/plData'

export function usePL() {
  const { filters } = useGlobalFilters()
  const { viewType, comparisonBase, businessUnit } = filters
  const period = filters.period ? `${filters.period.year}-${String(filters.period.month).padStart(2, '0')}` : '2026-06'

  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [usingMock, setUsingMock] = useState(false)

  useEffect(() => {
    setLoading(true)
    const params = buildParams({
      period_id: period,
      view_id: viewType,
      base_id: comparisonBase,
      bu_id: businessUnit || undefined,
    })

    api.computation
      .get(`/pl/statement${params}`)
      .then((data: any) => {
        setRows(transformPLRows(data.rows || []))
        setUsingMock(false)
        setLoading(false)
      })
      .catch(() => {
        setRows(MOCK_PL_DATA)
        setUsingMock(true)
        setLoading(false)
      })
  }, [viewType, comparisonBase, period, businessUnit])

  return { rows, margins: MOCK_MARGINS, loading, usingMock }
}
