import { cn } from '@/utils/theme'

interface SLABadgeProps {
  hours: number
}

export function SLABadge({ hours }: SLABadgeProps) {
  const label = hours < 1 ? '<1h' : hours < 24 ? `${Math.round(hours)}h` : `${Math.round(hours / 24)}d`

  const variant =
    hours < 12 ? 'green' : hours < 48 ? 'amber' : 'red'

  const variantStyles = {
    green: 'bg-[rgba(45,212,168,.12)] text-emerald',
    amber: 'bg-[rgba(251,191,36,.12)] text-amber',
    red: 'bg-[rgba(249,112,102,.12)] text-coral animate-pulse',
  }

  return (
    <span
      className={cn(
        'text-[7px] font-bold px-1.5 py-0.5 rounded-[10px] tracking-[0.3px]',
        variantStyles[variant],
      )}
    >
      {label}
    </span>
  )
}
