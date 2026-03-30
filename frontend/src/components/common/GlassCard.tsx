import { cn } from '@/utils/theme'

interface GlassCardProps {
  children: React.ReactNode
  className?: string
  hover?: boolean
  onClick?: () => void
}

export function GlassCard({ children, className, hover = false, onClick }: GlassCardProps) {
  return (
    <div
      className={cn(
        'glass-card transition-all duration-200',
        hover && 'glass-card-clickable cursor-pointer hover:-translate-y-0.5 hover:shadow-lg hover:border-[rgba(0,168,199,.2)]',
        className,
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick() } : undefined}
    >
      {children}
    </div>
  )
}
