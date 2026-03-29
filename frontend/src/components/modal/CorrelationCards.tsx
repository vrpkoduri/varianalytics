interface Correlation {
  account: string
  pct: number
  favorable: boolean
  hypothesis: string
  confidence: number
}

interface CorrelationCardsProps {
  data: Correlation[]
}

export function CorrelationCards({ data }: CorrelationCardsProps) {
  if (data.length === 0) return null

  return (
    <div>
      <span className="section-label">CORRELATED VARIANCES</span>
      <div className="space-y-1.5 mt-1.5">
        {data.map((corr) => {
          const dotColor = corr.favorable ? 'var(--emerald)' : 'var(--coral)'
          const pctColor = corr.favorable ? 'var(--emerald)' : 'var(--coral)'

          return (
            <div
              key={corr.account}
              className="p-2.5 rounded-lg"
              style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
              }}
            >
              <div className="flex items-center gap-2 mb-1">
                {/* Color dot */}
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ background: dotColor }}
                />
                {/* Account + pct */}
                <span className="text-[11px] font-medium text-tx-primary">
                  {corr.account}
                </span>
                <span
                  className="text-[10px] font-semibold ml-auto"
                  style={{ color: pctColor }}
                >
                  {corr.pct >= 0 ? '+' : ''}{corr.pct.toFixed(1)}%
                </span>
              </div>

              {/* Hypothesis */}
              <div className="text-[10px] text-tx-secondary leading-snug">
                {corr.hypothesis}
              </div>

              {/* Confidence */}
              <div className="text-[9px] text-tx-tertiary mt-1">
                Confidence: {corr.confidence}%
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
