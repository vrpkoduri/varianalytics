import { ReportCard } from './ReportCard'
import type { ReportItem } from '@/mocks/reportsData'

interface ReportsListProps {
  reports: ReportItem[]
  onPreview: (type: 'flash' | 'period' | 'board') => void
}

export function ReportsList({ reports, onPreview }: ReportsListProps) {
  if (!reports || reports.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-sm text-text-secondary">No reports generated yet.</p>
        <p className="text-xs text-text-secondary mt-1 opacity-60">
          Use the Templates tab to generate your first report, or run the engine from Admin &rarr; Engine Control.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2.5">
      {reports.map((r) => (
        <ReportCard key={r.id} report={r} onPreview={() => onPreview(r.previewType)} />
      ))}
    </div>
  )
}
