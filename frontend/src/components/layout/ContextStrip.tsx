import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { useUser } from '@/context/UserContext'
import { ViewType, ComparisonBase } from '@/types/index'
import { cn } from '@/utils/theme'

const PERSONAS = [
  { key: 'analyst', icon: '\u25A6', label: 'Analyst' },
  { key: 'director', icon: '\u25C9', label: 'Director' },
  { key: 'cfo', icon: '\u25C8', label: 'CFO' },
  { key: 'bu', icon: '\u25A3', label: 'BU Lead' },
] as const

const TIME_AGGS = [
  { key: ViewType.MTD, label: 'MTD' },
  { key: ViewType.QTD, label: 'QTD' },
  { key: ViewType.YTD, label: 'YTD' },
] as const

const BASES = [
  { key: ComparisonBase.BUDGET, label: 'Budget' },
  { key: ComparisonBase.FORECAST, label: 'Fcst' },
  { key: ComparisonBase.PRIOR_YEAR, label: 'PY' },
] as const

interface ContextStripProps {
  onFocusToggle: () => void
}

export default function ContextStrip({ onFocusToggle }: ContextStripProps) {
  const { persona, setPersona } = useUser()
  const { filters, setViewType, setComparisonBase } = useGlobalFilters()

  return (
    <div className="h-10 bg-[rgba(0,26,77,.35)] backdrop-blur-lg border-b border-[rgba(0,168,199,.08)] flex items-center justify-between px-6">
      {/* Left — Persona pills */}
      <div className="flex items-center gap-1.5">
        {PERSONAS.map((p) => {
          const isActive = p.key === persona
          return (
            <button
              key={p.key}
              onClick={() => setPersona(p.key)}
              className={cn(
                'flex items-center gap-1.5 px-3.5 py-1 rounded-full border cursor-pointer transition-all duration-200',
                isActive
                  ? 'bg-gradient-to-br from-[rgba(0,168,199,.18)] to-[rgba(0,168,199,.08)] border-[rgba(0,168,199,.25)]'
                  : 'border-white/[.06] hover:border-[rgba(0,168,199,.2)] hover:bg-[rgba(0,168,199,.04)]'
              )}
            >
              <span
                className={cn(
                  'w-5 h-5 rounded-full flex items-center justify-center text-[10px]',
                  isActive
                    ? 'bg-[rgba(0,168,199,.2)] text-teal'
                    : 'bg-white/[.04] text-white/25'
                )}
              >
                {p.icon}
              </span>
              <span
                className={cn(
                  'text-[11px]',
                  isActive ? 'font-semibold text-teal' : 'font-medium text-white/30'
                )}
              >
                {p.label}
              </span>
            </button>
          )
        })}
      </div>

      {/* Center — Time Agg + Base */}
      <div className="flex items-center gap-2">
        {/* Time agg group */}
        <div className="flex gap-0.5 bg-white/[.03] rounded-[5px] p-[1px] border border-white/[.06]">
          {TIME_AGGS.map((t) => {
            const isActive = filters.viewType === t.key
            return (
              <button
                key={t.key}
                onClick={() => setViewType(t.key)}
                className={cn(
                  'px-2.5 py-[3px] rounded-[4px] text-[10px] font-semibold transition-colors duration-150 cursor-pointer',
                  isActive ? 'bg-[rgba(0,168,199,.15)] text-teal' : 'text-white/30 hover:text-white/50'
                )}
              >
                {t.label}
              </button>
            )
          })}
        </div>

        <span className="text-[10px] text-[rgba(167,226,240,.3)] px-0.5">vs</span>

        {/* Comparison base group */}
        <div className="flex gap-0.5 bg-white/[.03] rounded-[5px] p-[1px] border border-white/[.06]">
          {BASES.map((b) => {
            const isActive = filters.comparisonBase === b.key
            return (
              <button
                key={b.key}
                onClick={() => setComparisonBase(b.key)}
                className={cn(
                  'px-2.5 py-[3px] rounded-[4px] text-[10px] font-semibold transition-colors duration-150 cursor-pointer',
                  isActive ? 'bg-[rgba(0,168,199,.15)] text-teal' : 'text-white/30 hover:text-white/50'
                )}
              >
                {b.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Right — Focus mode */}
      <button
        onClick={onFocusToggle}
        className="text-[10px] px-3 py-1 rounded-[5px] border border-white/[.08] text-white/35 hover:text-white/60 hover:border-white/15 transition-all cursor-pointer"
      >
        &#x27F3; Focus
      </button>
    </div>
  )
}
