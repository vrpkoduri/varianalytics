interface DonutProgressProps {
  approved: number
  reviewed: number
  draft: number
}

export function DonutProgress({ approved, reviewed, draft }: DonutProgressProps) {
  const total = approved + reviewed + draft
  const size = 48
  const strokeWidth = 3
  const r = size / 2 - strokeWidth
  const circumference = 2 * Math.PI * r

  // Segment arcs
  const approvedLen = total > 0 ? (approved / total) * circumference : 0
  const reviewedLen = total > 0 ? (reviewed / total) * circumference : 0
  const draftLen = total > 0 ? (draft / total) * circumference : circumference

  const approvedOffset = 0
  const reviewedOffset = -approvedLen
  const draftOffset = -(approvedLen + reviewedLen)

  return (
    <div
      className="px-2.5 py-2 rounded-lg border border-border mb-2.5"
      style={{ background: 'var(--card)' }}
    >
      <div className="text-[7px] font-bold text-teal uppercase tracking-[0.6px] mb-1.5">
        CLOSE PROGRESS
      </div>
      <div className="flex items-center gap-3">
        {/* SVG donut */}
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="flex-shrink-0">
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-white/[.06]"
          />
          {/* Draft arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="var(--tx-tertiary)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${draftLen} ${circumference - draftLen}`}
            strokeDashoffset={draftOffset}
            strokeLinecap="round"
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
          {/* Reviewed arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="var(--gold)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${reviewedLen} ${circumference - reviewedLen}`}
            strokeDashoffset={reviewedOffset}
            strokeLinecap="round"
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
          {/* Approved arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="var(--emerald)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${approvedLen} ${circumference - approvedLen}`}
            strokeDashoffset={approvedOffset}
            strokeLinecap="round"
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
          {/* Center text */}
          <text
            x={size / 2}
            y={size / 2}
            textAnchor="middle"
            dominantBaseline="central"
            className="fill-tx-primary text-[10px] font-bold"
          >
            {total}
          </text>
        </svg>

        {/* Legend */}
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-1 text-[8px]">
            <span className="text-emerald">&#x25CF;</span>
            <span className="text-tx-secondary">{approved} approved</span>
          </div>
          <div className="flex items-center gap-1 text-[8px]">
            <span className="text-gold">&#x25CF;</span>
            <span className="text-tx-secondary">{reviewed} reviewed</span>
          </div>
          <div className="flex items-center gap-1 text-[8px]">
            <span className="text-tx-tertiary">&#x25CF;</span>
            <span className="text-tx-secondary">{draft} draft</span>
          </div>
        </div>
      </div>
    </div>
  )
}
