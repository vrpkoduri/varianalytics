import { cn } from '@/utils/theme'

interface BatchActionBarProps {
  selectedCount: number
  onBatchAction: () => void
}

export function BatchActionBar({ selectedCount, onBatchAction }: BatchActionBarProps) {
  if (selectedCount === 0) return null

  return (
    <div
      className={cn(
        'flex items-center justify-between px-4 py-2 rounded-lg',
        'bg-[rgba(0,168,199,.06)] border border-[rgba(0,168,199,.15)]',
        'animate-slide-down',
      )}
    >
      <span className="text-[11px] font-bold text-teal">
        {selectedCount} selected
      </span>
      <button
        type="button"
        onClick={onBatchAction}
        className={cn(
          'text-[10px] font-semibold px-3 py-1 rounded-button',
          'bg-gradient-to-r from-cobalt to-teal text-white',
          'hover:shadow-button-hover transition-all duration-150',
        )}
      >
        Mark reviewed
      </button>
    </div>
  )
}
