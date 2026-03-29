import { useState, useEffect } from 'react'
import { cn } from '@/utils/theme'
import { Sparkline } from '@/components/charts/Sparkline'
import type { MockKPICard } from '@/mocks/dashboardData'

function useCountUp(target: number, duration = 800) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    let start = 0
    const increment = target / (duration / 16)
    const timer = setInterval(() => {
      start += increment
      if (start >= target) {
        setCount(target)
        clearInterval(timer)
      } else {
        setCount(Math.round(start))
      }
    }, 16)
    return () => clearInterval(timer)
  }, [target, duration])
  return count
}

interface KPICardProps {
  card: MockKPICard
}

export function KPICard({ card }: KPICardProps) {
  const count = useCountUp(card.value)
  const deltaColor = card.favorable ? 'text-emerald' : 'text-coral'
  const deltaSign = card.delta >= 0 ? '+' : ''

  return (
    <div className="glass-card glass-card-clickable p-4 relative overflow-hidden cursor-pointer">
      <div className="section-label mb-1">{card.label}</div>
      <div className="flex items-end justify-between">
        <div>
          <div className="text-kpi font-bold text-tx-primary">
            {card.prefix}{count.toLocaleString()}{card.suffix}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className={cn('text-[11px] font-semibold', deltaColor)}>
              {deltaSign}{card.delta}%
            </span>
            <span className="text-[9px] text-tx-tertiary">{card.comparatorLabel}</span>
          </div>
        </div>
        <div className="opacity-30 absolute right-3 bottom-3">
          <Sparkline data={card.sparkData} width={70} height={28} color="#00A8C7" opacity={0.4} />
        </div>
      </div>
    </div>
  )
}
