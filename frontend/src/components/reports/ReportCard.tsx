import { GlassCard } from '@/components/common/GlassCard'
import { Badge, type BadgeVariant } from '@/components/common/Badge'
import type { ReportItem } from '@/mocks/reportsData'

interface ReportCardProps {
  report: ReportItem
  onPreview: () => void
}

const STATUS_MAP: Record<ReportItem['status'], { variant: BadgeVariant; label: string }> = {
  ready: { variant: 'emerald', label: 'Ready' },
  draft: { variant: 'amber', label: 'Draft' },
  sent: { variant: 'teal', label: 'Sent' },
}

export function ReportCard({ report, onPreview }: ReportCardProps) {
  const status = STATUS_MAP[report.status]

  return (
    <GlassCard className="p-3 px-4">
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <div className="font-display text-[13px] font-bold truncate" title={report.name}>
            {report.name}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[9px] text-tx-tertiary whitespace-nowrap">{report.date}</span>
            <Badge variant={status.variant}>{status.label}</Badge>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0 ml-4">
          <button
            onClick={onPreview}
            className="px-2.5 py-1 rounded-button text-[8px] font-semibold border border-[rgba(255,255,255,.12)] text-tx-secondary hover:text-white hover:border-teal/40 transition-colors"
          >
            Preview
          </button>
          <button
            className="px-2.5 py-1 rounded-button text-[8px] font-semibold border border-[rgba(255,255,255,.08)] text-tx-tertiary opacity-50 cursor-not-allowed"
            disabled
          >
            Distribute
          </button>
          <button
            className={`px-2.5 py-1 rounded-button text-[8px] font-semibold border transition-colors ${
              report.status === 'ready' || report.status === 'sent'
                ? 'border-[rgba(255,255,255,.12)] text-tx-secondary hover:text-white hover:border-teal/40 cursor-pointer'
                : 'border-[rgba(255,255,255,.08)] text-tx-tertiary opacity-50 cursor-not-allowed'
            }`}
            disabled={report.status !== 'ready' && report.status !== 'sent'}
            onClick={() => {
              if (report.id) {
                window.open(`/api/reports/reports/download/${report.id}`, '_blank')
              }
            }}
          >
            Download
          </button>
        </div>
      </div>
    </GlassCard>
  )
}
