interface AnalystGroupHeaderProps {
  name: string
  initials: string
  reviewedCount: number
  onBulkApprove: () => void
}

export function AnalystGroupHeader({ name, initials, reviewedCount, onBulkApprove }: AnalystGroupHeaderProps) {
  return (
    <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-border">
      <div className="flex items-center gap-2">
        <div className="w-[30px] h-[30px] rounded-lg bg-[rgba(0,168,199,.1)] text-teal text-[10px] font-bold flex items-center justify-center">
          {initials}
        </div>
        <span className="text-[11px] font-semibold">{name}</span>
      </div>

      {reviewedCount > 0 && (
        <button
          onClick={onBulkApprove}
          className="text-[8px] font-semibold text-white px-3 py-1 rounded-md"
          style={{ background: 'linear-gradient(135deg, #002C77, #00A8C7)' }}
        >
          Approve ({reviewedCount})
        </button>
      )}
    </div>
  )
}
