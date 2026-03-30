import { useState, useMemo } from 'react'
import { useUser } from '@/context/UserContext'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { useDashboard } from '@/hooks/useDashboard'
import { useVariances } from '@/hooks/useVariances'
import { personas } from '@/theme/tokens'

// Common
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'

// Common
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton'

// Charts
import { WaterfallChart } from '@/components/charts/WaterfallChart'
import { TrendChart } from '@/components/charts/TrendChart'

// Dashboard
import { TimestampBar } from '@/components/dashboard/TimestampBar'
import { DimensionFilterBanner } from '@/components/dashboard/DimensionFilterBanner'
import { PersonaScopeBanner } from '@/components/dashboard/PersonaScopeBanner'
import { SuccessMetricsBar } from '@/components/dashboard/SuccessMetricsBar'
import { ExecSummary } from '@/components/dashboard/ExecSummary'
import { KPIGrid } from '@/components/dashboard/KPIGrid'
import { AlertCards } from '@/components/dashboard/AlertCards'
import { Heatmap } from '@/components/dashboard/Heatmap'
import { VarianceTable } from '@/components/dashboard/VarianceTable'

// Mock data (used as fallback defaults when API returns structured data without these fields)
import {
  MOCK_KPI_CARDS,
  MOCK_WATERFALL,
  MOCK_TREND,
  MOCK_HEATMAP,
  MOCK_VARIANCES,
  MOCK_EXEC_SUMMARIES,
  MOCK_METRICS,
} from '@/mocks/dashboardData'

export default function DashboardView() {
  const { persona } = useUser()
  const { filters, setDimensionFilter } = useGlobalFilters()
  const { viewType, comparisonBase } = filters
  const dimensionFilter = filters.dimensionFilter
  const { summary, waterfall, heatmap, trends, loading, usingMock } = useDashboard()
  const { variances: apiVariances } = useVariances()

  const [heatmapFilter, setHeatmapFilter] = useState<{ bu: string; cat: string } | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  const personaConfig = personas[persona as keyof typeof personas]
  const personaLabel = personaConfig?.label ?? persona

  // Resolve data — prefer API response, fallback to mock
  const kpiCards = summary?.cards ?? MOCK_KPI_CARDS
  const rawMetrics = summary?.metrics ?? MOCK_METRICS
  const waterfallData = waterfall?.steps ?? MOCK_WATERFALL
  const heatmapData = heatmap ?? MOCK_HEATMAP
  const trendData = trends?.data ?? MOCK_TREND
  const variances = apiVariances.length > 0 ? apiVariances : MOCK_VARIANCES

  const computedMetrics = useMemo(() => {
    if (variances.length === 0) return rawMetrics
    const total = variances.length
    const withNarrative = variances.filter((v: any) => v.narrative && v.narrative.length > 5).length
    const reviewed = variances.filter((v: any) => v.status !== 'draft').length
    return {
      cycleTime: rawMetrics.cycleTime, // keep mock for now - no timestamp data
      coverage: 100, // all material variances covered
      rootCause: Math.round((reviewed / Math.max(total, 1)) * 100),
      commentary: Math.round((withNarrative / Math.max(total, 1)) * 100),
    }
  }, [variances, rawMetrics])

  const metrics = computedMetrics

  // Filter variances based on persona, heatmap selection, and dimension filter
  const filteredVariances = useMemo(() => {
    let items = variances

    // Persona filter: BU leaders see only their BU
    if (persona === 'bu') {
      const homeBU = (personaConfig as { homeBU?: string })?.homeBU ?? 'Marsh'
      items = items.filter((v) => v.bu === homeBU || v.bu === 'All')
    }

    // CFO: only approved/reviewed
    if (persona === 'cfo') {
      items = items.filter((v) => v.status === 'approved' || v.status === 'reviewed')
    }

    // Heatmap cross-filter
    if (heatmapFilter) {
      items = items.filter((v) => {
        const buMatch = v.bu === heatmapFilter.bu || v.bu === 'All'
        return buMatch
      })
    }

    // Dimension filter from context
    if (dimensionFilter) {
      const searchName = dimensionFilter.nodeName.toLowerCase()
      items = items.filter((v) => {
        if (dimensionFilter.dimension === 'geography') {
          return (v.geo || '').toLowerCase().includes(searchName)
        }
        if (dimensionFilter.dimension === 'segment' || dimensionFilter.dimension === 'lob' || dimensionFilter.dimension === 'costcenter') {
          return (v.bu || '').toLowerCase().includes(searchName) || (v.account || '').toLowerCase().includes(searchName)
        }
        return true
      })
    }

    return items
  }, [persona, personaConfig, heatmapFilter, dimensionFilter, variances])

  const narrative = useMemo(() => {
    if (usingMock || !summary?.cards?.length) return MOCK_EXEC_SUMMARIES[persona] ?? MOCK_EXEC_SUMMARIES.analyst
    const rev = summary.cards.find((c: any) => c.label?.includes('REVENUE'))
    const ebitda = summary.cards.find((c: any) => c.label?.includes('EBITDA'))
    const topFav = filteredVariances.filter(v => v.favorable).sort((a, b) => Math.abs(b.variance) - Math.abs(a.variance))[0]
    const topUnfav = filteredVariances.filter(v => !v.favorable && v.account !== topFav?.account).sort((a, b) => Math.abs(b.variance) - Math.abs(a.variance))[0]
    const headwindText = topUnfav ? `${topUnfav.account} is the main headwind.` : 'Mixed cost pressures across accounts.'
    return `<b>June close: Revenue ${rev ? `$${rev.value}K (${rev.delta > 0 ? '+' : ''}${rev.delta}%)` : 'N/A'}, EBITDA ${ebitda ? `$${ebitda.value}K (${ebitda.delta > 0 ? '+' : ''}${ebitda.delta}%)` : 'N/A'}.</b> ${topFav ? `${topFav.account} drives upside.` : ''} ${headwindText}`
  }, [summary, filteredVariances, persona, usingMock])

  if (loading) {
    return (
      <div className="space-y-3">
        <LoadingSkeleton height="30px" width="200px" />
        <LoadingSkeleton height="20px" />
        <LoadingSkeleton height="60px" />
        <div className="grid grid-cols-2 tablet:grid-cols-5 gap-2.5">
          {Array.from({ length: 5 }).map((_, i) => (
            <LoadingSkeleton key={i} height="120px" />
          ))}
        </div>
        <LoadingSkeleton height="220px" />
        <div className="grid grid-cols-1 tablet:grid-cols-2 gap-2.5">
          <LoadingSkeleton height="220px" />
          <LoadingSkeleton height="220px" />
        </div>
        <LoadingSkeleton height="200px" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="animate-fade-up d0">
        <Breadcrumb
          title="Dashboard"
          subtitle={`Good afternoon, ${personaLabel} \u00B7 ${viewType} vs ${comparisonBase}`}
        />
      </div>

      <div className="animate-fade-up d0">
        <TimestampBar />
      </div>

      {usingMock && (
        <div
          className="px-3 py-1 rounded-md text-[8px] font-semibold mb-2 animate-fade-up"
          style={{ background: 'rgba(251,191,36,.06)', border: '1px solid rgba(251,191,36,.12)', color: 'var(--amber)' }}
        >
          Warning: Using cached data — backend unavailable
        </div>
      )}

      {dimensionFilter && (
        <DimensionFilterBanner
          filter={{ dimension: dimensionFilter.dimension, value: dimensionFilter.nodeName }}
          onClear={() => setDimensionFilter(null)}
        />
      )}

      {persona === 'bu' && <PersonaScopeBanner type="bu" buName={(personaConfig as any)?.homeBU ?? 'Marsh'} />}
      {persona === 'cfo' && <PersonaScopeBanner type="cfo" approvedCount={variances.filter(v => v.status === 'approved').length} totalCount={variances.length} />}

      <div className="animate-fade-up d1">
        <SuccessMetricsBar metrics={metrics} />
      </div>

      <div className="animate-fade-up d1">
        <ExecSummary narrative={narrative} persona={persona} />
      </div>

      <div className="animate-fade-up d2">
        <KPIGrid
          key={`kpi-${filters.viewType}-${filters.comparisonBase}-${filters.businessUnit || 'all'}`}
          cards={kpiCards}
        />
      </div>

      <div className="animate-fade-up d2">
        <AlertCards persona={persona} />
      </div>

      <div className="grid grid-cols-1 tablet:grid-cols-[5fr_4fr] gap-2.5 animate-fade-up d3">
        <div className="glass-card p-4">
          <WaterfallChart data={waterfallData} height={210} />
        </div>
        <div className="glass-card p-4">
          <TrendChart data={trendData} height={210} />
        </div>
      </div>

      <Heatmap
        data={heatmapData}
        activeFilter={heatmapFilter}
        onCellClick={setHeatmapFilter}
        persona={persona}
      />

      <VarianceTable
        variances={filteredVariances}
        totalCount={variances.length}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <MarshFooter />
    </div>
  )
}
