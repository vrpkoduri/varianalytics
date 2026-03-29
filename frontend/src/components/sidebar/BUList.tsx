import { cn } from '@/utils/theme'

interface BUListProps {
  activeBU: string | null
  onBUSelect: (buId: string | null) => void
  variantCounts?: Record<string, number>
}

const BUS = [
  { id: null, name: 'All' },
  { id: 'marsh', name: 'Marsh' },
  { id: 'mercer', name: 'Mercer' },
  { id: 'guy_carpenter', name: 'Guy Carpenter' },
  { id: 'oliver_wyman', name: 'Oliver Wyman' },
  { id: 'mmc_corporate', name: 'MMC Corporate' },
] as const

export function BUList({ activeBU, onBUSelect, variantCounts }: BUListProps) {
  return (
    <div>
      <h6 className="text-[7px] font-bold text-teal uppercase tracking-[1.2px] mt-2.5 mb-1 px-1">
        Business Unit
      </h6>
      <div className="flex flex-col">
        {BUS.map((bu) => {
          const isActive = activeBU === bu.id
          const count = bu.id ? variantCounts?.[bu.id] : undefined
          return (
            <button
              key={bu.id ?? 'all'}
              onClick={() => onBUSelect(bu.id as string | null)}
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
