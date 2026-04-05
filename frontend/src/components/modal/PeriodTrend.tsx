import type { VarianceDetail } from '@/context/ModalContext'
import { formatPercent } from '@/utils/formatters'

interface PeriodTrendProps {
  data: VarianceDetail
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export function PeriodTrend({ data }: PeriodTrendProps) {
  const spark = data.sparkData
  if (spark.length < 3) return null

  // Last 3 periods
  const last3 = spark.slice(-3)
  // Map to percentage-like values (treat sparkData as % proxies)
  const labels = [MONTHS[3], MONTHS[4], MONTHS[5]] // Apr, May, Jun (current period context)

  return (
    <div>
      <span className="section-label">PERIOD TREND</span>
      <div className="flex gap-1.5 mt-1.5">
        {last3.map((val, idx) => {
          const isLast = idx === last3.length - 1
          return (
            <div
              key={idx}
              className="flex-1 p-2 rounded-lg text-center"
              style={{
                background: 'var(--surface)',
                border: isLast
                  ? '1px solid #00A8C7'
                  : '1px solid var(--border)',
              }}
            >
              <div className="text-[8px] text-tx-tertiary mb-0.5">
                {labels[idx]}
              </div>
              <div
                className="text-[12px] font-bold"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  color: isLast ? '#00A8C7' : 'var(--tx-primary)',
                }}
              >
                {formatPercent(val)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
