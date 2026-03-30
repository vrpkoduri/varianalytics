interface SegmentedProgressBarProps {
  approved: number
  reviewed: number
  draft: number
}

export function SegmentedProgressBar({ approved, reviewed, draft }: SegmentedProgressBarProps) {
  const total = approved + reviewed + draft
  if (total === 0) return null

  const approvedPct = (approved / total) * 100
  const reviewedPct = (reviewed / total) * 100
  const draftPct = (draft / total) * 100

  return (
    <div className="animate-fade-up d1">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[8px] font-bold text-teal uppercase tracking-[1.2px]">
          Review progress
        </span>
        <span className="text-[9px] text-tx-tertiary">
          {total} variances
        </span>
      </div>

      <div className="flex h-1.5 rounded-full overflow-hidden bg-[var(--border)]">
        <div
          className="bg-emerald transition-all duration-500"
          style={{ flex: `${approvedPct} 0 0%` }}
        />
        <div
          className="bg-gold transition-all duration-500"
          style={{ flex: `${reviewedPct} 0 0%` }}
        />
        <div
          className="bg-tx-tertiary transition-all duration-500"
          style={{ flex: `${draftPct} 0 0%` }}
        />
      </div>

      <div className="flex gap-4 mt-1.5">
        <span className="text-[8px] text-emerald font-medium">{approved} approved</span>
        <span className="text-[8px] text-gold font-medium">{reviewed} reviewed</span>
        <span className="text-[8px] text-tx-tertiary font-medium">{draft} draft</span>
      </div>
    </div>
  )
}
