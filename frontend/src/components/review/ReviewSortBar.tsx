import { SearchBar } from '@/components/common/SearchBar'
import { cn } from '@/utils/theme'

interface ReviewSortBarProps {
  sortBy: string
  searchQuery: string
  onSortChange: () => void
  onSearchChange: (value: string) => void
}

const sortLabels: Record<string, string> = {
  varpct: 'Impact',
  sla: 'SLA',
  account: 'Name',
}

export function ReviewSortBar({ sortBy, searchQuery, onSortChange, onSearchChange }: ReviewSortBarProps) {
  return (
    <div className="flex items-center gap-2 animate-fade-up d3">
      <SearchBar
        value={searchQuery}
        onChange={onSearchChange}
        placeholder="Search account, BU, geo..."
        className="flex-1"
      />
      <button
        type="button"
        onClick={onSortChange}
        className={cn(
          'text-[9px] font-semibold px-2.5 py-1 rounded-button',
          'border border-border bg-[var(--card)] text-tx-secondary',
          'hover:border-[var(--border-hover)] hover:text-tx-primary transition-all duration-150',
          'flex items-center gap-1 whitespace-nowrap',
        )}
      >
        {sortLabels[sortBy] ?? sortBy}
        <span className="text-[8px] text-tx-tertiary">{'\u21C5'}</span>
      </button>
    </div>
  )
}
