import { useState, useEffect } from 'react'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { api, buildParams } from '@/utils/api'
import {
  transformSummaryCards,
  transformWaterfallSteps,
  transformTrendData,
  transformHeatmap,
} from '@/utils/transformers'
import {
  MOCK_KPI_CARDS,
  MOCK_WATERFALL,
  MOCK_HEATMAP,
  MOCK_TREND,
  MOCK_METRICS,
} from '@/mocks/dashboardData'

export function useDashboard() {
  const { filters } = useGlobalFilters()
  const { viewType, comparisonBase, businessUnit } = filters
  const period = filters.period ? `${filters.period.year}-${String(filters.period.month).padStart(2, '0')}` : '2026-06'

  const [summary, setSummary] = useState<any>(null)
  const [waterfall, setWaterfall] = useState<any>(null)
  const [heatmap, setHeatmap] = useState<any>(null)
  const [trends, setTrends] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [usingMock, setUsingMock] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)

    const params = buildParams({
      period_id: period,
      view_id: viewType,
      base_id: comparisonBase,
      bu_id: businessUnit || undefined,
    })

    Promise.all([
      api.computation.get(`/dashboard/summary${params}`),
      api.computation.get(`/dashboard/waterfall${params}`),
      api.computation.get(
        `/dashboard/heatmap${buildParams({ period_id: period, base_id: comparisonBase })}`,
      ),
      api.computation.get(
        `/dashboard/trends${buildParams({ base_id: comparisonBase, periods: 12 })}`,
      ),
    ])
      .then(([s, w, h, t]) => {
        setSummary({
          cards: transformSummaryCards(s?.cards || []),
          metrics: s?.metrics || MOCK_METRICS,
        })
        setWaterfall({ steps: transformWaterfallSteps(w?.steps || []) })
        setHeatmap(transformHeatmap(h))
        setTrends({ data: transformTrendData(t?.data || []) })
        setUsingMock(false)
        setLoading(false)
      })
      .catch(() => {
        // Fallback to mock data
        setSummary({ cards: MOCK_KPI_CARDS, metrics: MOCK_METRICS })
        setWaterfall({ steps: MOCK_WATERFALL })
        setHeatmap(MOCK_HEATMAP)
        setTrends({ data: MOCK_TREND })
        setUsingMock(true)
        setLoading(false)
      })
  }, [viewType, comparisonBase, period, businessUnit])

  return { summary, waterfall, heatmap, trends, loading, error, usingMock }
}
