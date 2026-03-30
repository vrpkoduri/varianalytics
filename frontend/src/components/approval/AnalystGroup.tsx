import { GlassCard } from '@/components/common/GlassCard'
import { AnalystGroupHeader } from './AnalystGroupHeader'
import { ApprovalItem } from './ApprovalItem'
import type { AnalystGroupData, ApprovalVariance } from '@/mocks/approvalData'

interface AnalystGroupProps {
  group: AnalystGroupData
  onApproveItem: (id: string) => void
  onHoldItem: (id: string) => void
  onBulkApprove: () => void
  onOpenModal: (item: ApprovalVariance) => void
}

export function AnalystGroup({ group, onApproveItem, onHoldItem, onBulkApprove, onOpenModal }: AnalystGroupProps) {
  const reviewedCount = group.items.filter(i => i.status === 'reviewed').length

  return (
    <GlassCard className="mb-2.5 overflow-hidden animate-fade-up">
      <AnalystGroupHeader
        name={group.name}
        initials={group.initials}
        reviewedCount={reviewedCount}
        onBulkApprove={onBulkApprove}
      />
      {group.items.map(item => (
        <ApprovalItem
          key={item.id}
          item={item}
          onApprove={() => onApproveItem(item.id)}
          onHold={() => onHoldItem(item.id)}
          onOpenModal={() => onOpenModal(item)}
        />
      ))}
    </GlassCard>
  )
}
