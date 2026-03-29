import { formatCurrency } from '@/utils/formatters'

interface DecompositionSectionProps {
  data: Array<{ label: string; value: number; pct: number }>
}

export function DecompositionSection({ data }: DecompositionSectionProps) {
  if (data.length === 0) return null

  const maxPct = Math.max(...data.map((d) => d.pct))

  return (
    <div>
      <span className="section-label">DECOMPOSITION</span>
      <div className="flex flex-wrap gap-1.5 mt-1.5">
        {data.map((item, idx) => {
          const barW = maxPct > 0 ? `${(item.pct / maxPct) * 100}%` : '0%'
          const isPositive = item.value >= 0
          const valueColor = isPositive ? 'var(--emerald)' : 'var(--coral)'

          return (
            <div
              key={item.label}
              className="min-w-[64px] p-2 rounded-lg"
              style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
              }}
            >
              {/* Label */}
              <div className="text-[8px] text-tx-tertiary mb-0.5">{item.label}</div>

              {/* Value */}
              <div className="text-[11px] font-bold" style={{ color: valueColor }}>
                {isPositive ? '+' : ''}{formatCurrency(Math.abs(item.value))} ({item.pct}%)
              </div>

              {/* Animated bar */}
              <div
                className="mt-1 rounded-full overflow-hidden"
                style={{ height: '3px', background: 'var(--border)' }}
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    '--bar-w': barW,
                    width: barW,
                    background: valueColor,
                    animation: `bar-slide 0.5s cubic-bezier(.22,1,.36,1) ${idx * 100}ms both`,
                  } as React.CSSProperties}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* Inline keyframes for bar animation */}
      <style>{`
        @keyframes bar-slide {
          from { width: 0; }
          to { width: var(--bar-w); }
        }
      `}</style>
    </div>
  )
}
