import { GlassCard } from '@/components/common/GlassCard'
import { cn } from '@/utils/theme'

interface Counts {
  awaiting: number
  reviewed: number
  approved: number
  all: number
}

interface StatusCounterCardsProps {
  counts: Counts
  activeFilter: string
  onFilterChange: (filter: string) => void
}

const cards: Array<{ key: string; label: string; color: string }> = [
  { key: 'awaiting', label: 'Awaiting Review', color: 'text-tx-secondary' },
  { key: 'reviewed', label: 'Reviewed', color: 'text-gold' },
  { key: 'approved', label: 'Approved', color: 'text-emerald' },
  { key: 'all', label: 'Total', color: 'text-tx-tertiary' },
]

export function StatusCounterCards({ counts, activeFilter, onFilterChange }: StatusCounterCardsProps) {
  return (
    <div className="grid grid-cols-4 gap-2.5 animate-fade-up d2">
      {cards.map(({ key, label, color }) => (
        <GlassCard
          key={key}
          hover
          onClick={() => onFilterChange(key)}
          className={cn(
            'p-3 text-center cursor-pointer transition-all duration-150',
            activeFilter === key && 'border-teal ring-1 ring-teal/20',
          )}
        >
          <div className={cn('font-display text-[26px] font-bold', color)}>
            {counts[key as keyof Counts]}
          </div>
          <div className="text-[9px] text-tx-tertiary uppercase tracking-[0.5px] mt-0.5">
            {label}
          </div>
        </GlassCard>
      ))}
    </div>
  )
}
