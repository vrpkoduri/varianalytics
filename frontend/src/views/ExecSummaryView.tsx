/**
 * Executive Summary landing page.
 *
 * Narrative-first view for CFO, Director, and Board personas.
 * Tells the financial story with supporting visuals.
 */

import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'
import { AlertCards } from '@/components/dashboard/AlertCards'
import { SectionNarrativeCard } from '@/components/executive/SectionNarrativeCard'
import { ProfitabilitySection } from '@/components/executive/ProfitabilitySection'
import { DownloadBar } from '@/components/executive/DownloadBar'
import { useExecutiveSummary } from '@/hooks/useExecutiveSummary'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { useUser } from '@/context/UserContext'

export default function ExecSummaryView() {
  const { execSummary, sections, kpiCards, nettingAlerts, trendAlerts, loading } = useExecutiveSummary()
  const { filters } = useGlobalFilters()
  const { persona } = useUser()

  const periodLabel = filters.period?.label || 'Current Period'
  const baseLabel = filters.comparisonBase === 'FORECAST' ? 'Forecast' : filters.comparisonBase === 'PRIOR_YEAR' ? 'Prior Year' : 'Budget'

  if (loading) {
    return (
      <div className="space-y-3">
        <Breadcrumb title="Executive Summary" subtitle="Loading..." />
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  // Extract section narratives by name
  const revenueSection = sections.find((s: any) => s.sectionName === 'Revenue')
  const cogsSection = sections.find((s: any) => s.sectionName === 'COGS')
  const opexSection = sections.find((s: any) => s.sectionName === 'OpEx')
  const profitSection = sections.find((s: any) => s.sectionName === 'Profitability')

  // Extract KPI values for display (use any for flexible field access)
  const getKPI = (name: string): any => kpiCards.find((c: any) =>
    (c.metricName || c.metric_name || '').toLowerCase().includes(name.toLowerCase())
  )
  const revenue = getKPI('revenue')
  const ebitda = getKPI('ebitda')
  const netIncome = getKPI('net income') || getKPI('net_income')
  const grossProfit = getKPI('gross profit') || getKPI('gross_profit')

  // Compute margins
  const revActual: number = revenue?.actual || 1
  const grossMargin = grossProfit ? ((grossProfit.actual || 0) / revActual * 100) : 0
  const ebitdaMargin = ebitda ? ((ebitda.actual || 0) / revActual * 100) : 0
  const netMargin = netIncome ? ((netIncome.actual || 0) / revActual * 100) : 0

  return (
    <div className="space-y-3">
      {/* Header */}
      <Breadcrumb title="Executive Summary" subtitle={`${periodLabel} vs ${baseLabel}`} />

      {/* Headline */}
      <div className="glass-card p-5 border-l-2 border-l-teal animate-fade-up d1">
        <span className="section-label">THE HEADLINE</span>
        <p className="text-[15px] font-body font-semibold text-text mt-2 leading-relaxed">
          {execSummary?.headline || 'Executive summary not available for this period.'}
        </p>
        {execSummary?.crossBuThemes && execSummary.crossBuThemes.length > 0 && (
          <div className="flex gap-2 mt-2">
            {execSummary.crossBuThemes.map((t: any, i: number) => (
              <span key={i} className="text-[9px] px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
                {t.theme || t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 tablet:grid-cols-4 gap-2.5 animate-fade-up d2">
        {[revenue, ebitda, grossProfit, netIncome].filter(Boolean).map((card: any, i) => {
          const name = card.metricName || card.metric_name || 'Metric'
          const actual = card.actual || card.actualAmount || 0
          const variance = card.varianceAmount || card.variance_amount || 0
          const pct = card.variancePct || card.variance_pct || 0
          const isFav = card.isFavorable ?? card.is_favorable ?? variance > 0

          return (
            <div key={i} className="glass-card p-3 text-center">
              <div className="text-[8px] text-text-secondary uppercase tracking-wider mb-1">{name}</div>
              <div className="text-[20px] font-body font-bold text-text">
                ${(actual / 1000).toFixed(0)}K
              </div>
              <div className={`text-[11px] font-semibold ${isFav ? 'text-emerald' : 'text-coral'}`}>
                {pct > 0 ? '+' : ''}{pct.toFixed(1)}% (${(variance / 1000).toFixed(1)}K)
              </div>
            </div>
          )
        })}
      </div>

      {/* Section Narratives: Revenue + Costs */}
      <div className="grid grid-cols-1 tablet:grid-cols-2 gap-2.5 animate-fade-up d3">
        {revenueSection && (
          <SectionNarrativeCard
            sectionName="Revenue"
            narrative={revenueSection.narrative || ''}
            drivers={revenueSection.keyDrivers || []}
          />
        )}
        <div className="space-y-2.5">
          {cogsSection && (
            <SectionNarrativeCard
              sectionName="Cost of Revenue"
              narrative={cogsSection.narrative || ''}
              drivers={cogsSection.keyDrivers || []}
            />
          )}
          {opexSection && (
            <SectionNarrativeCard
              sectionName="Operating Expenses"
              narrative={opexSection.narrative || ''}
              drivers={opexSection.keyDrivers || []}
            />
          )}
        </div>
      </div>

      {/* Profitability */}
      <div className="animate-fade-up d4">
        <ProfitabilitySection
          narrative={profitSection?.narrative || 'Profitability data not available.'}
          grossMargin={grossMargin}
          ebitdaMargin={ebitdaMargin}
          netMargin={netMargin}
        />
      </div>

      {/* Risk Items */}
      <div className="animate-fade-up d5">
        <AlertCards persona={persona} nettingAlerts={nettingAlerts} trendAlerts={trendAlerts} />
      </div>

      {/* Full Narrative */}
      {execSummary?.fullNarrative && (
        <div className="glass-card p-5 animate-fade-up d6">
          <span className="section-label">DETAILED NARRATIVE</span>
          <div className="mt-3 space-y-3">
            {execSummary.fullNarrative.split('\n\n').map((para: string, i: number) => (
              <p key={i} className="text-[11px] text-text leading-relaxed">{para}</p>
            ))}
          </div>
        </div>
      )}

      {/* Download */}
      <div className="animate-fade-up d7">
        <DownloadBar />
      </div>

      <MarshFooter />
    </div>
  )
}
