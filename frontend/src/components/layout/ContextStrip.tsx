import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { useUser } from '@/context/UserContext'
import { useTheme } from '@/context/ThemeContext'
import { usePeriods } from '@/hooks/usePeriods'
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
  const { filters, setPeriod, setViewType, setComparisonBase } = useGlobalFilters()
  const { periods } = usePeriods()
  const { isDark } = useTheme()

  const currentPeriodId = filters.period
    ? `${filters.period.year}-${String(filters.period.month).padStart(2, '0')}`
    : ''

  // Theme-adaptive colors for the context strip
  const stripBg = isDark ? 'bg-[rgba(0,26,77,.35)]' : 'bg-[rgba(0,44,119,.06)]'
  const stripBorder = isDark ? 'border-[rgba(0,168,199,.08)]' : 'border-border'
  const inactiveText = isDark ? 'text-white/30' : 'text-tx-tertiary'
  const inactiveHover = isDark ? 'hover:text-white/50' : 'hover:text-tx-secondary'
  const inactiveBg = isDark ? 'bg-white/[.04]' : 'bg-tx-tertiary/10'
  const inactiveBorder = isDark ? 'border-white/[.06]' : 'border-border'
  const groupBg = isDark ? 'bg-white/[.03]' : 'bg-surface/50'
  const groupBorder = isDark ? 'border-white/[.06]' : 'border-border'
  const vsColor = isDark ? 'text-[rgba(167,226,240,.3)]' : 'text-tx-tertiary'
  const focusText = isDark ? 'text-white/35 hover:text-white/60' : 'text-tx-tertiary hover:text-tx-primary'
  const focusBorder = isDark ? 'border-white/[.08] hover:border-white/15' : 'border-border hover:border-border-hover'
  const selectBg = isDark ? 'bg-white/[.03]' : 'bg-surface'
  const selectBorder = isDark ? 'border-white/[.06]' : 'border-border'

  return (
    <div className={cn('h-10 backdrop-blur-lg border-b flex items-center justify-between px-4 overflow-x-auto', stripBg, stripBorder)}>
      {/* Left — Persona pills */}
      <div className="flex items-center gap-1.5 shrink-0">
        {PERSONAS.map((p) => {
          const isActive = p.key === persona
          return (
            <button
              key={p.key}
              onClick={() => setPersona(p.key)}
              className={cn(
                'flex items-center gap-1.5 px-2.5 py-1 rounded-full border cursor-pointer transition-all duration-200',
                isActive
                  ? 'bg-gradient-to-br from-[rgba(0,168,199,.18)] to-[rgba(0,168,199,.08)] border-[rgba(0,168,199,.25)]'
                  : cn(inactiveBorder, 'hover:border-[rgba(0,168,199,.2)] hover:bg-[rgba(0,168,199,.04)]')
              )}
            >
              <span
                className={cn(
                  'w-5 h-5 rounded-full flex items-center justify-center text-[10px]',
                  isActive
                    ? 'bg-[rgba(0,168,199,.2)] text-teal'
                    : cn(inactiveBg, inactiveText)
                )}
              >
                {p.icon}
              </span>
              <span
                className={cn(
                  'text-[11px]',
                  isActive ? 'font-semibold text-teal' : cn('font-medium', inactiveText)
                )}
              >
                {p.label}
              </span>
            </button>
          )
        })}
      </div>

      {/* Center — Time Agg + Base */}
      <div className="flex items-center gap-2 min-w-0 shrink-0">
        {/* Time agg group */}
        <div className={cn('flex gap-0.5 rounded-[5px] p-[1px] border', groupBg, groupBorder)}>
          {TIME_AGGS.map((t) => {
            const isActive = filters.viewType === t.key
            return (
              <button
                key={t.key}
                onClick={() => setViewType(t.key)}
                className={cn(
                  'px-2.5 py-[3px] rounded-[4px] text-[10px] font-semibold transition-colors duration-150 cursor-pointer',
                  isActive ? 'bg-[rgba(0,168,199,.15)] text-teal' : cn(inactiveText, inactiveHover)
                )}
              >
                {t.label}
              </button>
            )
          })}
        </div>

        <span className={cn('text-[10px] px-0.5', vsColor)}>vs</span>

        {/* Comparison base group */}
        <div className={cn('flex gap-0.5 rounded-[5px] p-[1px] border', groupBg, groupBorder)}>
          {BASES.map((b) => {
            const isActive = filters.comparisonBase === b.key
            return (
              <button
                key={b.key}
                onClick={() => setComparisonBase(b.key)}
                className={cn(
                  'px-2.5 py-[3px] rounded-[4px] text-[10px] font-semibold transition-colors duration-150 cursor-pointer',
                  isActive ? 'bg-[rgba(0,168,199,.15)] text-teal' : cn(inactiveText, inactiveHover)
                )}
              >
                {b.label}
              </button>
            )
          })}
        </div>

        {/* E3: Period selector */}
        <div className="flex items-center gap-1 ml-2">
          <select
            value={currentPeriodId}
            onChange={(e) => {
              const selected = periods.find((p) => p.periodId === e.target.value)
              if (selected) {
                setPeriod({ year: selected.year, month: selected.month, label: selected.label })
              }
            }}
            className={cn('rounded-[5px] px-2 py-[3px] text-[10px] font-semibold text-teal cursor-pointer appearance-none focus:outline-none focus:border-[rgba(0,168,199,.3)] transition-colors border', selectBg, selectBorder)}
            style={{ minWidth: '90px' }}
          >
            {periods.length === 0 && (
              <option value="">Loading...</option>
            )}
            {periods.map((p) => (
              <option key={p.periodId} value={p.periodId} className="bg-card text-tx-primary">
                {p.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Right — Focus mode */}
      <button
        onClick={onFocusToggle}
        className={cn('text-[10px] px-3 py-1 rounded-[5px] border transition-all cursor-pointer', focusBorder, focusText)}
      >
        &#x27F3; Focus
      </button>
    </div>
  )
}
