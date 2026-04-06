import { useState, useEffect } from 'react'
import { api } from '@/utils/api'
import { useFilterParams } from '@/hooks/useFilterParams'
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
  const { query, buildQuery } = useFilterParams()

  const [summary, setSummary] = useState<any>(null)
  const [waterfall, setWaterfall] = useState<any>(null)
  const [heatmap, setHeatmap] = useState<any>(null)
  const [trends, setTrends] = useState<any>(null)
  const [nettingAlerts, setNettingAlerts] = useState<any[] | undefined>(undefined)
  const [trendAlerts, setTrendAlerts] = useState<any[] | undefined>(undefined)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [usingMock, setUsingMock] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)

    // All 6 dashboard endpoints use the same unified filter params
    // Trends endpoint gets extra "periods" param for trailing window
    const trendsQuery = buildQuery({ periods: 12 })

    Promise.all([
      api.computation.get(`/dashboard/summary${query}`),
      api.computation.get(`/dashboard/waterfall${query}`),
      api.computation.get(`/dashboard/heatmap${query}`),
      api.computation.get(`/dashboard/trends${trendsQuery}`),
      api.computation.get(`/dashboard/alerts/netting${query}`),
      api.computation.get(`/dashboard/alerts/trends${query}`),
    ])
      .then(([s, w, h, t, na, ta]) => {
        setSummary({
          cards: transformSummaryCards(s?.cards || []),
          metrics: s?.metrics || MOCK_METRICS,
        })
        setWaterfall({ steps: transformWaterfallSteps(w?.steps || []) })
        setHeatmap(transformHeatmap(h))
        setTrends({ data: transformTrendData(t?.data || []) })
        setNettingAlerts(na?.alerts?.length > 0 ? na.alerts : undefined)
        setTrendAlerts(ta?.alerts?.length > 0 ? ta.alerts : undefined)
        setUsingMock(false)
        setLoading(false)
      })
      .catch(() => {
        setSummary({ cards: MOCK_KPI_CARDS, metrics: MOCK_METRICS })
        setWaterfall({ steps: MOCK_WATERFALL })
        setHeatmap(MOCK_HEATMAP)
        setTrends({ data: MOCK_TREND })
        setNettingAlerts(undefined)
        setTrendAlerts(undefined)
        setUsingMock(true)
        setLoading(false)
      })
  }, [query, buildQuery])

  return { summary, waterfall, heatmap, trends, nettingAlerts, trendAlerts, loading, error, usingMock }
}
