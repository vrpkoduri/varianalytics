interface ReportGateProps {
  pendingCount: number
  onApproveAllReviewed: () => void
}

export function ReportGate({ pendingCount, onApproveAllReviewed }: ReportGateProps) {
  const isGreen = pendingCount === 0

  return (
    <div
      className="px-3.5 py-2.5 rounded-lg mb-3.5 flex items-center justify-between animate-fade-up"
      style={{
        background: isGreen ? 'rgba(45,212,168,.06)' : 'rgba(251,191,36,.06)',
        border: isGreen ? '1px solid rgba(45,212,168,.12)' : '1px solid rgba(251,191,36,.12)',
      }}
    >
      <span
        className="text-[11px] font-medium"
        style={{ color: isGreen ? '#2DD4A8' : '#FBBF24' }}
      >
        {isGreen
          ? '\u2713 Report gate: All approved \u2014 ready for distribution'
          : `\u26A0 Report gate: ${pendingCount} pending \u2014 distribution blocked`}
      </span>

      {!isGreen && (
        <button
          onClick={onApproveAllReviewed}
          className="text-[8px] font-semibold text-white px-3 py-1 rounded-md"
          style={{ background: 'linear-gradient(135deg, #002C77, #00A8C7)' }}
        >
          Approve all reviewed
        </button>
      )}
    </div>
  )
}
