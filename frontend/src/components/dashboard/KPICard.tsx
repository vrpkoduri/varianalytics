import { useState, useEffect, useRef } from 'react'
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

  // E12: Copy KPI value to clipboard
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(`${card.prefix}${card.value}${card.suffix}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  // E13: Flash effect on value change
  const [flash, setFlash] = useState(false)
  const prevValue = useRef(card.value)
  useEffect(() => {
    if (prevValue.current !== card.value && prevValue.current !== 0) {
      setFlash(true)
      setTimeout(() => setFlash(false), 1000)
    }
    prevValue.current = card.value
  }, [card.value])

  return (
    <div className={cn(
      'glass-card glass-card-clickable p-4 relative overflow-hidden cursor-pointer transition-all',
      flash ? 'ring-2 ring-teal/30' : ''
    )}>
      <div className="section-label mb-1">{card.label}</div>
      <div className="flex items-end justify-between">
        <div>
          <div
            className="text-kpi font-bold font-display text-tx-primary animate-glow cursor-pointer relative"
            onClick={handleCopy}
            title="Click to copy"
          >
            {card.prefix}{count.toLocaleString()}{card.suffix}
            {copied && (
              <span className="absolute -right-12 top-0 text-[8px] text-teal font-semibold">
                Copied!
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className={cn('text-[11px] font-semibold', deltaColor)}>
              {deltaSign}{card.delta}%
            </span>
            <span className="text-[9px] text-tx-tertiary">{card.comparatorLabel}</span>
          </div>
        </div>
        <div className="opacity-[0.06] absolute right-3 bottom-3">
          <Sparkline data={card.sparkData} width={70} height={28} color="#00A8C7" opacity={0.4} />
        </div>
      </div>
    </div>
  )
}
