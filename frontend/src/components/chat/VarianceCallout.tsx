import { Badge, type BadgeVariant } from '@/components/common/Badge'

interface VarianceCalloutProps {
  account: string
  delta: string
  description: string
  favorable: boolean
  status: string
}

const STATUS_BADGE: Record<string, BadgeVariant> = {
  approved: 'emerald',
  reviewed: 'gold',
  draft: 'gray',
}

export function VarianceCallout({ account, delta, description, favorable, status }: VarianceCalloutProps) {
  const arrow = favorable ? '\u25B2' : '\u25BC'

  return (
    <div
      className={`my-2 px-2.5 py-1.5 rounded-md text-[10px] border-l-2 ${
        favorable
          ? 'bg-emerald-surface border-emerald'
          : 'bg-coral-surface border-coral'
      }`}
    >
      <span className="text-tx-primary">
        <b>{arrow} {account}</b> {delta}
      </span>
      <span className="text-tx-secondary"> — {description} </span>
      <Badge variant={STATUS_BADGE[status] || 'gray'} className="ml-1">
        {status}
      </Badge>
    </div>
  )
}
