import { useState, useEffect } from 'react'
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
import { api } from '@/utils/api'

export default function ReportsView() {
  const { persona } = useUser()
  const [activeTab, setActiveTab] = useState<'reports' | 'schedules' | 'templates'>('reports')
  const [previewType, setPreviewType] = useState<'flash' | 'period' | 'board' | null>(null)

  const [apiReports, setApiReports] = useState<any[] | null>(null)
  const [apiSchedules, setApiSchedules] = useState<any[] | null>(null)
  const [apiTemplates, setApiTemplates] = useState<any[] | null>(null)
  const [_loadingReports, setLoadingReports] = useState(false)

  useEffect(() => {
    setLoadingReports(true)
    Promise.all([
      api.reports.get('/reports/history').catch(() => null),
      api.reports.get('/scheduling/schedules').catch(() => null),
      api.reports.get('/reports/templates').catch(() => null),
    ]).then(([reports, schedules, templates]) => {
      if (Array.isArray(reports)) setApiReports(reports)
      else if (reports?.items) setApiReports(reports.items)
      if (Array.isArray(schedules)) setApiSchedules(schedules)
      if (Array.isArray(templates)) setApiTemplates(templates)
      setLoadingReports(false)
    })
  }, [])

  // Persona filtering for reports
  const filteredReports = MOCK_REPORTS.filter((r) => {
    if (persona === 'bu') return r.scope === 'bu' || r.scope === 'all'
    if (persona === 'cfo') return true // CFO sees all
    return r.scope !== 'cfo' // Analyst/Director skip CFO-only
  })

  // Use API data with mock fallback — map API shape to component shape
  const reports = apiReports
    ? apiReports.map((r: any) => ({
        id: r.jobId || r.job_id || r.id,
        name: r.name || `Report ${r.format} — ${r.periodId || r.period_id || ''}`,
        status: (r.status || '').toLowerCase() === 'completed' ? 'ready' : (r.status?.toLowerCase() || 'draft'),
        scope: 'all' as const,
        previewType: (r.format || 'pdf').toLowerCase() === 'xlsx' ? 'period' as const : 'flash' as const,
        date: r.createdAt || r.created_at || '',
      }))
    : filteredReports
  const schedules = apiSchedules ?? MOCK_SCHEDULES
  const templates = apiTemplates ?? MOCK_TEMPLATES

  return (
    <div className="space-y-3">
      <Breadcrumb title="Reports" subtitle="Report generation & distribution" />

      {persona === 'bu' && <PersonaScopeBanner type="bu" buName="Marsh" />}

      <ReportSubTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === 'reports' && (
        <ReportsList reports={reports} onPreview={setPreviewType} />
      )}
      {activeTab === 'schedules' && <SchedulesList schedules={schedules} />}
      {activeTab === 'templates' && (
        <TemplatesList templates={templates} onGenerate={(type) => setPreviewType(type)} />
      )}

      <MarshFooter />

      <ReportPreviewOverlay reportType={previewType} onClose={() => setPreviewType(null)} />
    </div>
  )
}
