import { Badge } from '@/components/common/Badge'
import { ReviewCheckbox } from './ReviewCheckbox'
import { SLABadge } from './SLABadge'
import { cn } from '@/utils/theme'
import type { ReviewVariance } from '@/mocks/reviewData'
import type { BadgeVariant } from '@/components/common/Badge'

interface ReviewItemCollapsedProps {
  item: ReviewVariance
  isChecked: boolean
  isExpanded: boolean
  onCheck: () => void
  onToggle: () => void
}

const statusBadge: Record<string, { label: string; variant: BadgeVariant }> = {
  draft: { label: 'AI Draft', variant: 'gray' },
  reviewed: { label: 'Reviewed', variant: 'gold' },
  approved: { label: 'Approved', variant: 'emerald' },
}

const typeBadge: Record<string, { label: string; variant: BadgeVariant }> = {
  material: { label: 'Material', variant: 'coral' },
  netted: { label: 'Netted', variant: 'purple' },
  trending: { label: 'Trending', variant: 'amber' },
}

const edgeBadgeVariant: Record<string, BadgeVariant> = {
  edited: 'teal',
  New: 'emerald',
  synth: 'purple',
  'No budget': 'coral',
}

function formatVariance(value: number): string {
  const abs = Math.abs(value)
  const sign = value >= 0 ? '+' : '-'
  return `${sign}$${abs >= 1000 ? `${(abs / 1000).toFixed(1)}K` : abs.toLocaleString()}`
}

export function ReviewItemCollapsed({ item, isChecked, isExpanded, onCheck, onToggle }: ReviewItemCollapsedProps) {
  const sb = statusBadge[item.status]
  const tb = typeBadge[item.type]

  return (
    <div
      className={cn(
        'flex items-center gap-2.5 px-3 py-2 cursor-pointer transition-all duration-150',
        'hover:bg-[rgba(0,168,199,.03)]',
        isExpanded && 'bg-[rgba(0,168,199,.04)]',
      )}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onToggle() }}
    >
      {/* Checkbox */}
      <ReviewCheckbox checked={isChecked} onChange={onCheck} />

      {/* Color bar */}
      <div
        className={cn(
          'w-[3px] h-6 rounded-full shrink-0',
          item.favorable ? 'bg-emerald' : 'bg-coral',
        )}
      />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-bold text-[var(--tx-primary)] truncate">
            {item.account}
          </span>
          <Badge variant={sb.variant} className="text-[7px] px-1.5 py-0">{sb.label}</Badge>
          <Badge variant={tb.variant} className="text-[7px] px-1.5 py-0">{tb.label}</Badge>
          {item.edgeBadge && (
            <Badge variant={edgeBadgeVariant[item.edgeBadge] ?? 'gray'} className="text-[7px] px-1.5 py-0">
              {item.edgeBadge}
            </Badge>
          )}
        </div>
        <div className="text-[9px] text-tx-tertiary mt-0.5">
          {item.bu} &middot; {item.geo}
        </div>
      </div>

      {/* Variance amount */}
      <div
        className={cn(
          'font-display text-[17px] font-bold shrink-0',
          item.favorable ? 'text-emerald' : 'text-coral',
        )}
      >
        {formatVariance(item.variance)}
      </div>

      {/* Variance pct */}
      <div
        className={cn(
          'text-[10px] font-semibold shrink-0 w-12 text-right',
          item.favorable ? 'text-emerald' : 'text-coral',
        )}
      >
        {item.variancePct > 0 ? '+' : ''}{item.variancePct}%
      </div>

      {/* SLA badge */}
      {item.sla > 0 && (
        <SLABadge hours={item.sla} />
      )}

      {/* Chevron */}
      <span className="text-[10px] text-tx-tertiary shrink-0 w-3 text-center">
        {isExpanded ? '\u25BE' : '\u25B8'}
      </span>
    </div>
  )
}
