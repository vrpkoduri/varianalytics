import { GlassCard } from '@/components/common/GlassCard'
import { ReviewItemCollapsed } from './ReviewItemCollapsed'
import { ReviewItemExpanded } from './ReviewItemExpanded'
import type { ReviewVariance } from '@/mocks/reviewData'

interface ReviewListProps {
  items: ReviewVariance[]
  expandedIds: Set<string>
  checkedIds: Set<string>
  onToggleExpand: (id: string) => void
  onToggleCheck: (id: string) => void
  onOpenModal: (item: ReviewVariance) => void
  onConfirm: (id: string) => void
  onHypothesisFeedback: (itemId: string, hyIndex: number, feedback: -1 | 0 | 1) => void
}

export function ReviewList({
  items,
  expandedIds,
  checkedIds,
  onToggleExpand,
  onToggleCheck,
  onOpenModal,
  onConfirm,
  onHypothesisFeedback,
}: ReviewListProps) {
  if (items.length === 0) {
    return (
      <GlassCard className="p-8 text-center animate-fade-up d4">
        <div className="text-[11px] text-tx-tertiary">
          No variances match this filter.
        </div>
      </GlassCard>
    )
  }

  return (
    <GlassCard className="divide-y divide-border overflow-hidden animate-fade-up d4">
      {items.map((item) => (
        <div key={item.id}>
          <ReviewItemCollapsed
            item={item}
            isChecked={checkedIds.has(item.id)}
            isExpanded={expandedIds.has(item.id)}
            onCheck={() => onToggleCheck(item.id)}
            onToggle={() => onToggleExpand(item.id)}
          />
          {expandedIds.has(item.id) && (
            <ReviewItemExpanded
              item={item}
              onOpenModal={() => onOpenModal(item)}
              onConfirm={() => onConfirm(item.id)}
              onHypothesisFeedback={(hyIndex, feedback) =>
                onHypothesisFeedback(item.id, hyIndex, feedback)
              }
            />
          )}
        </div>
      ))}
    </GlassCard>
  )
}
