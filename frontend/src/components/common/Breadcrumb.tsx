import { cn } from '@/utils/theme'

interface BreadcrumbProps {
  title: string
  subtitle?: string
}

export function Breadcrumb({ title, subtitle }: BreadcrumbProps) {
  return (
    <div className={cn('flex items-center justify-between mb-3 animate-fade-up')}>
      <em className="font-display text-page-title not-italic">{title}</em>
      {subtitle && (
        <span className="text-[8px] text-tx-tertiary tracking-[2.5px] uppercase">
          {subtitle}
        </span>
      )}
    </div>
  )
}
