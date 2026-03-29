import { useState, useMemo } from 'react'
import { useUser } from '@/context/UserContext'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { personas } from '@/theme/tokens'

// Common
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'

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

// Mock data
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
  const { filters } = useGlobalFilters()
  const { viewType, comparisonBase } = filters

  const [heatmapFilter, setHeatmapFilter] = useState<{ bu: string; cat: string } | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [dimensionFilter, setDimensionFilter] = useState<{ dimension: string; value: string } | null>(null)

  const personaConfig = personas[persona as keyof typeof personas]
  const personaLabel = personaConfig?.label ?? persona

  // Filter variances based on persona, heatmap selection, and dimension filter
  const filteredVariances = useMemo(() => {
    let items = MOCK_VARIANCES

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

    // Dimension filter
    if (dimensionFilter) {
      items = items.filter((v) => {
        if (dimensionFilter.dimension === 'BU') return v.bu === dimensionFilter.value
        if (dimensionFilter.dimension === 'Geo') return v.geo === dimensionFilter.value
        return true
      })
    }

    return items
  }, [persona, personaConfig, heatmapFilter, dimensionFilter])

  const narrative = MOCK_EXEC_SUMMARIES[persona] ?? MOCK_EXEC_SUMMARIES.analyst

  return (
    <div className="space-y-3">
      <Breadcrumb
        title="Dashboard"
        subtitle={`Good afternoon, ${personaLabel} \u00B7 ${viewType} vs ${comparisonBase}`}
      />

      <TimestampBar />

      {dimensionFilter && (
        <DimensionFilterBanner
          filter={dimensionFilter}
          onClear={() => setDimensionFilter(null)}
        />
      )}

      {persona === 'bu' && <PersonaScopeBanner type="bu" buName="Marsh" />}
      {persona === 'cfo' && <PersonaScopeBanner type="cfo" approvedCount={18} totalCount={42} />}

      <SuccessMetricsBar metrics={MOCK_METRICS} />

      <ExecSummary narrative={narrative} persona={persona} />

      <KPIGrid cards={MOCK_KPI_CARDS} />

      <AlertCards persona={persona} />

      <div className="grid grid-cols-1 tablet:grid-cols-[5fr_4fr] gap-2.5 animate-fade-up d3">
        <div className="glass-card p-4">
          <WaterfallChart data={MOCK_WATERFALL} height={210} />
        </div>
        <div className="glass-card p-4">
          <TrendChart data={MOCK_TREND} height={210} />
        </div>
      </div>

      <Heatmap
        data={MOCK_HEATMAP}
        activeFilter={heatmapFilter}
        onCellClick={setHeatmapFilter}
        persona={persona}
      />

      <VarianceTable
        variances={filteredVariances}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <MarshFooter />
    </div>
  )
}
