import { useState, useEffect, useMemo } from 'react'
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

  const computedMargins = useMemo(() => {
    if (!rows.length) return MOCK_MARGINS
    const find = (term: string) => rows.find((r: any) => r.name?.toLowerCase().includes(term))
    const rev = find('revenue')?.actual || find('gross revenue')?.actual
    const gp = find('gross profit')?.actual
    const ebitda = find('ebitda')?.actual
    const opInc = find('operating income')?.actual || find('op income')?.actual
    const netInc = find('net income')?.actual
    if (!rev || rev === 0) return MOCK_MARGINS
    const pct = (val: number | undefined) => val ? Math.round((val / rev) * 1000) / 10 : 0
    return [
      { id: 'gross', label: 'Gross Margin', value: pct(gp), delta: '', color: 'var(--emerald)' },
      { id: 'ebitda', label: 'EBITDA', value: pct(ebitda), delta: '', color: 'var(--teal, #00A8C7)' },
      { id: 'op', label: 'Op Margin', value: pct(opInc), delta: '', color: '#00A8C7' },
      { id: 'tax', label: 'Tax Rate', value: 25.0, delta: '', color: 'var(--amber)' },
      { id: 'net', label: 'Net Margin', value: pct(netInc), delta: '', color: 'var(--gold)' },
    ]
  }, [rows])

  return { rows, margins: computedMargins, loading, usingMock }
}
