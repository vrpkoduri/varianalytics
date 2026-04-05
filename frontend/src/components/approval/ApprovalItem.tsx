import { Badge } from '@/components/common/Badge'
import type { ApprovalVariance } from '@/mocks/approvalData'

interface ApprovalItemProps {
  item: ApprovalVariance
  onApprove: () => void
  onHold: () => void
  onOpenModal: () => void
}

function formatVariance(value: number, pct: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${Math.abs(value / 1000).toFixed(1)}K (${sign}${pct.toFixed(1)}%)`
}

export function ApprovalItem({ item, onApprove, onHold, onOpenModal }: ApprovalItemProps) {
  const isApproved = item.status === 'approved'

  return (
    <div
      className="flex items-center gap-2 px-3.5 py-2.5 border-b border-border cursor-pointer hover:bg-[rgba(0,168,199,.02)] transition-colors"
      onClick={onOpenModal}
    >
      {/* Status dot */}
      <div
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ background: isApproved ? '#2DD4A8' : '#FBBF24' }}
      />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-medium truncate">{item.account}</span>
          <Badge variant={item.favorable ? 'emerald' : 'coral'}>
            {formatVariance(item.variance, item.variancePct)}
          </Badge>
          {item.isEdited && (
            <Badge variant="gold">Edited</Badge>
          )}
        </div>
        {(item as any).narrativeDetail && (
          <div className="text-[8px] text-tx-secondary mt-0.5 truncate max-w-[500px] opacity-70">
            {(item as any).narrativeDetail.slice(0, 140)}...
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {isApproved ? (
          <span className="text-[9px] font-semibold text-emerald">{'\u2713'} Approved</span>
        ) : (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); onApprove() }}
              className="text-[7px] font-semibold text-white px-2 py-0.5 rounded"
              style={{ background: 'linear-gradient(135deg, #002C77, #00A8C7)' }}
            >
              Approve
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onHold() }}
              className="text-[7px] font-semibold px-2 py-0.5 rounded border"
              style={{ color: '#F97066', borderColor: '#F97066' }}
            >
              Hold
            </button>
          </>
        )}
      </div>
    </div>
  )
}
