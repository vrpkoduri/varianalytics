import { useState } from 'react'
import { useUser } from '@/context/UserContext'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'
import { PersonaScopeBanner } from '@/components/dashboard/PersonaScopeBanner'
import { ReportSubTabs } from '@/components/reports/ReportSubTabs'
import { ReportsList } from '@/components/reports/ReportsList'
import { SchedulesList } from '@/components/reports/SchedulesList'
import { TemplatesList } from '@/components/reports/TemplatesList'
import { ReportPreviewOverlay } from '@/components/reports/ReportPreviewOverlay'
import { MOCK_REPORTS, MOCK_SCHEDULES, MOCK_TEMPLATES } from '@/mocks/reportsData'

export default function ReportsView() {
  const { persona } = useUser()
  const [activeTab, setActiveTab] = useState<'reports' | 'schedules' | 'templates'>('reports')
  const [previewType, setPreviewType] = useState<'flash' | 'period' | 'board' | null>(null)

  // Persona filtering for reports
  const filteredReports = MOCK_REPORTS.filter((r) => {
    if (persona === 'bu') return r.scope === 'bu' || r.scope === 'all'
    if (persona === 'cfo') return true // CFO sees all
    return r.scope !== 'cfo' // Analyst/Director skip CFO-only
  })

  return (
    <div className="space-y-3">
      <Breadcrumb title="Reports" subtitle="Report generation & distribution" />

      {persona === 'bu' && <PersonaScopeBanner type="bu" buName="Marsh" />}

      <ReportSubTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === 'reports' && (
        <ReportsList reports={filteredReports} onPreview={setPreviewType} />
      )}
      {activeTab === 'schedules' && <SchedulesList schedules={MOCK_SCHEDULES} />}
      {activeTab === 'templates' && (
        <TemplatesList templates={MOCK_TEMPLATES} onGenerate={(type) => setPreviewType(type)} />
      )}

      <MarshFooter />

      <ReportPreviewOverlay reportType={previewType} onClose={() => setPreviewType(null)} />
    </div>
  )
}
