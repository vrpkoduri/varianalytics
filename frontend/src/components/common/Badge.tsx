import { cn } from '@/utils/theme'

export type BadgeVariant = 'teal' | 'gold' | 'emerald' | 'coral' | 'amber' | 'purple' | 'gray'

interface BadgeProps {
  variant: BadgeVariant
  children: React.ReactNode
  className?: string
}

const variantStyles: Record<BadgeVariant, string> = {
  teal: 'bg-[rgba(0,168,199,.1)] text-teal',
  gold: 'bg-gold-surface text-gold',
  emerald: 'bg-emerald-surface text-emerald',
  coral: 'bg-coral-surface text-coral',
  amber: 'bg-amber-surface text-amber',
  purple: 'bg-purple-surface text-purple',
  gray: 'bg-[rgba(255,255,255,.05)] text-tx-tertiary',
}

export function Badge({ variant, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-block text-badge-xs px-2 py-0.5 rounded-badge font-semibold tracking-[0.5px]',
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  )
}
