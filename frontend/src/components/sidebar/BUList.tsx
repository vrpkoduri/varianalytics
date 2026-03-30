import { cn } from '@/utils/theme'

interface BUListProps {
  items: Array<{ id: string | null; name: string; varianceCount?: number }>
  activeId: string | null
  onSelect: (buId: string | null) => void
}

export function BUList({ items, activeId, onSelect }: BUListProps) {
  return (
    <div>
      <h6 className="text-[7px] font-bold text-teal uppercase tracking-[1.2px] mt-2.5 mb-1 px-1">
        Business Unit
      </h6>
      <div className="flex flex-col">
        {items.map((bu) => {
          const isActive = activeId === bu.id
          const count = bu.varianceCount
          return (
            <button
              key={bu.id ?? 'all'}
              onClick={() => onSelect(bu.id)}
              className={cn(
                'flex items-center gap-1 px-1.5 py-1 rounded-md text-[10px] font-medium cursor-pointer transition-all duration-150 text-left',
                isActive
                  ? 'bg-[rgba(0,168,199,.1)] text-teal font-semibold'
                  : 'text-tx-secondary hover:bg-[rgba(0,168,199,.06)] hover:text-tx-primary'
              )}
            >
              <span className="w-3.5 flex-shrink-0" />
              {bu.name}
              {count != null && count > 0 && (
                <span className="ml-auto text-[7px] font-bold text-teal bg-[rgba(0,168,199,.1)] rounded-md px-1">
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
