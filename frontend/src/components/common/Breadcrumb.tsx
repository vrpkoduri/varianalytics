import { cn } from '@/utils/theme'

interface BreadcrumbProps {
  title: string
  subtitle?: string
  filters?: { bu?: string; dimension?: string }
}

export function Breadcrumb({ title, subtitle, filters }: BreadcrumbProps) {
  // E6: Build breadcrumb trail from filters
  const trail = [title]
  if (filters?.bu) trail.push(filters.bu.replace(/_/g, ' '))
  if (filters?.dimension) trail.push(filters.dimension)

  return (
    <div className={cn('flex items-center justify-between mb-3 animate-fade-up')}>
      <div className="flex items-center gap-1">
        {trail.map((segment, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <span className="text-[10px] text-tx-tertiary">&rsaquo;</span>}
            <em className={cn(
              'font-display not-italic',
              i === 0 ? 'text-page-title' : 'text-[14px] text-teal'
            )}>
              {segment}
            </em>
          </span>
        ))}
      </div>
      {subtitle && (
        <span className="text-[8px] text-tx-tertiary tracking-[2.5px] uppercase">
          {subtitle}
        </span>
      )}
    </div>
  )
}
