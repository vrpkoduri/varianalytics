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
          'text-[10px] font-semibold px-3 py-1.5 rounded-lg flex-shrink-0',
          'border border-teal/30 bg-[rgba(0,168,199,0.06)] text-teal',
          'hover:bg-[rgba(0,168,199,0.12)] hover:text-tx-primary transition-all duration-150',
          'flex items-center gap-1.5 whitespace-nowrap',
        )}
      >
        {sortLabels[sortBy] ?? sortBy}
        <span className="text-[9px]">{'\u21C5'}</span>
      </button>
    </div>
  )
}
