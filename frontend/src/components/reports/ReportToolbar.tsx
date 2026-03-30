import { Badge } from '@/components/common/Badge'

interface ReportToolbarProps {
  title: string
  onClose: () => void
}

export function ReportToolbar({ title, onClose }: ReportToolbarProps) {
  return (
    <div className="sticky top-0 h-12 bg-cobalt flex items-center justify-between px-6 z-10 shrink-0">
      <div className="flex items-center gap-3">
        <span className="font-display text-[14px] font-bold text-white">{title}</span>
        <Badge variant="teal">MTD vs Budget</Badge>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => window.print()}
          className="px-3 py-1 rounded-button text-[8px] font-semibold text-white border border-[rgba(255,255,255,.25)] hover:border-[rgba(255,255,255,.5)] transition-colors"
        >
          Print
        </button>
        <button
          className="px-3 py-1 rounded-button text-[8px] font-semibold text-white border border-[rgba(255,255,255,.25)] opacity-50 cursor-not-allowed"
          disabled
        >
          Email
        </button>
        <button
          className="px-3 py-1 rounded-button text-[8px] font-semibold bg-gradient-to-r from-cobalt-light to-teal text-white shadow-[0_2px_8px_rgba(0,168,199,.2)] opacity-50 cursor-not-allowed"
          disabled
        >
          Download PDF
        </button>
        <button
          onClick={onClose}
          className="w-6 h-6 rounded-full border border-[rgba(255,255,255,.25)] text-white text-[12px] flex items-center justify-center hover:border-coral hover:text-coral transition-colors"
          aria-label="Close preview"
        >
          &times;
        </button>
      </div>
    </div>
  )
}
