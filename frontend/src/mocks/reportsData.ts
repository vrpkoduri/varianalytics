export interface ReportItem {
  id: string
  name: string
  status: 'ready' | 'draft' | 'sent'
  scope: 'all' | 'cfo' | 'bu'
  previewType: 'flash' | 'period' | 'board'
  date: string
}

export interface ScheduleItem {
  id: string
  name: string
  frequency: string
  nextRun: string
  isActive: boolean
}

export interface TemplateItem {
  id: string
  name: string
  type: string
  description: string
  previewType: 'flash' | 'period' | 'board'
}

export const MOCK_REPORTS: ReportItem[] = [
  { id: 'r1', name: 'June Period-End Package', status: 'ready', scope: 'all', previewType: 'period', date: 'Jun 30, 2026' },
  { id: 'r2', name: 'Q2 Board Package', status: 'draft', scope: 'cfo', previewType: 'board', date: 'Jun 30, 2026' },
  { id: 'r3', name: 'Executive Flash — June', status: 'sent', scope: 'all', previewType: 'flash', date: 'Jun 28, 2026' },
  { id: 'r4', name: 'Weekly Pulse', status: 'sent', scope: 'all', previewType: 'flash', date: 'Jun 24, 2026' },
  { id: 'r5', name: 'Marsh BU Digest', status: 'ready', scope: 'bu', previewType: 'period', date: 'Jun 30, 2026' },
]

export const MOCK_SCHEDULES: ScheduleItem[] = [
  { id: 's1', name: 'Weekly Pulse', frequency: 'Every Monday 8:00 AM', nextRun: 'Jul 1, 2026', isActive: true },
  { id: 's2', name: 'Monthly Flash', frequency: '1st business day', nextRun: 'Jul 1, 2026', isActive: true },
  { id: 's3', name: 'Board Package', frequency: 'Quarterly', nextRun: 'Sep 15, 2026', isActive: true },
  { id: 's4', name: 'BU Digest', frequency: 'Bi-weekly Friday', nextRun: 'Jul 5, 2026', isActive: false },
]

export const MOCK_TEMPLATES: TemplateItem[] = [
  { id: 't1', name: 'Period-End Package', type: 'PDF + PPTX', description: 'Full variance analysis with decomposition, narratives, and risk assessment', previewType: 'period' },
  { id: 't2', name: 'Executive Flash', type: 'PDF', description: 'One-page summary of key variances and KPIs', previewType: 'flash' },
  { id: 't3', name: 'BU Deep Dive', type: 'XLSX + PDF', description: 'Detailed BU-level analysis with drill-down data', previewType: 'period' },
  { id: 't4', name: 'Board Narrative', type: 'DOCX', description: 'Research-note style narrative for board consumption', previewType: 'board' },
]
