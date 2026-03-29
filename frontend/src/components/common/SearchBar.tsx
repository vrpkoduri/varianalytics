import { cn } from '@/utils/theme'

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

export function SearchBar({ value, onChange, placeholder = 'Search...', className }: SearchBarProps) {
  return (
    <div className={cn('relative', className)}>
      <svg
        className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-tx-tertiary"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={cn(
          'w-[190px] py-1 px-2.5 pl-7 rounded-button border border-border',
          'text-[10px] font-body bg-[var(--card)] text-[var(--tx-primary)]',
          'focus:border-teal focus:bg-surface focus:shadow-[0_0_0_2px_rgba(0,168,199,.1)]',
          'outline-none transition-all placeholder:text-tx-tertiary',
        )}
      />
    </div>
  )
}
