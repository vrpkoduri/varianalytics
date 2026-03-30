import { ReportCard } from './ReportCard'
import type { ReportItem } from '@/mocks/reportsData'

interface ReportsListProps {
  reports: ReportItem[]
  onPreview: (type: 'flash' | 'period' | 'board') => void
}

export function ReportsList({ reports, onPreview }: ReportsListProps) {
  return (
    <div className="space-y-2.5">
      {reports.map((r) => (
        <ReportCard key={r.id} report={r} onPreview={() => onPreview(r.previewType)} />
      ))}
    </div>
  )
}
