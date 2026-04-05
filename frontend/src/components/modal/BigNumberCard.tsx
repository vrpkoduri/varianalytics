import { GlassCard } from '@/components/common/GlassCard'
import { useCountUp } from '@/hooks/useCountUp'
import { formatCurrency, formatPercent } from '@/utils/formatters'
import type { VarianceDetail } from '@/context/ModalContext'

interface BigNumberCardProps {
  data: VarianceDetail
}

export function BigNumberCard({ data }: BigNumberCardProps) {
  const animatedValue = useCountUp(Math.abs(data.variance), 800)
  const sign = data.variance >= 0 ? '+' : '-'
  const colorClass = data.favorable ? 'text-emerald' : 'text-coral'
  const glowColor = data.favorable
    ? 'rgba(45,212,168,.3)'
    : 'rgba(249,112,102,.3)'

  return (
    <GlassCard className="p-4">
      <div className="flex items-baseline gap-2">
        {/* Big number */}
        <span
          className={`text-[30px] font-bold ${colorClass}`}
          style={{
            fontFamily: "'Inter', sans-serif",
            textShadow: `0 0 20px ${glowColor}`,
          }}
        >
          {sign}{formatCurrency(animatedValue)}
        </span>

        {/* Arrow + pct */}
        <span className={`text-[14px] font-semibold ${colorClass}`}>
          {data.favorable ? '\u25B2' : '\u25BC'} {formatPercent(data.variancePct)}
        </span>
      </div>

      {/* Favorable / Unfavorable label */}
      <div className="flex items-center gap-2 mt-1.5">
        <span
          className="text-[9px] font-semibold px-2 py-0.5 rounded-badge"
          style={{
            background: data.favorable
              ? 'var(--emerald-surface)'
              : 'var(--coral-surface)',
            color: data.favorable ? 'var(--emerald)' : 'var(--coral)',
          }}
        >
          {data.favorable ? 'Favorable' : 'Unfavorable'}
        </span>
      </div>

      {/* Confidence bar */}
      <div
        className="mt-3 rounded-full overflow-hidden"
        style={{ height: '4px', background: 'var(--border)' }}
      >
        <div
          className="h-full rounded-full"
          style={{
            width: data.projectedYE
              ? data.projectedYE.confidence === 'High'
                ? '90%'
                : data.projectedYE.confidence === 'Medium'
                  ? '60%'
                  : '30%'
              : '50%',
            background: '#00A8C7',
            transition: 'width 0.5s ease',
          }}
        />
      </div>

      {/* Projected YE */}
      {data.projectedYE && (
        <div
          className="mt-2 p-2 rounded-lg text-[10px]"
          style={{
            background: 'var(--amber-surface)',
            border: '1px solid rgba(251,191,36,.15)',
          }}
        >
          <span className="text-amber font-semibold">Projected YE:</span>{' '}
          <span className="text-tx-secondary">
            {data.projectedYE.amount >= 0 ? '+' : ''}
            {formatCurrency(data.projectedYE.amount)} ({data.projectedYE.confidence} confidence)
          </span>
        </div>
      )}
    </GlassCard>
  )
}
