export interface ApprovalVariance {
  id: string
  account: string
  bu: string
  geo: string
  variance: number
  variancePct: number
  favorable: boolean
  status: 'reviewed' | 'approved'
  assignedAnalyst: string
  isEdited: boolean
  varianceId?: string // maps to MOCK_MODAL_DATA
}

export interface AnalystGroupData {
  name: string
  initials: string
  items: ApprovalVariance[]
}

export const MOCK_APPROVAL_DATA: ApprovalVariance[] = [
  // Sarah Chen's items (4)
  { id: 'ap1', account: 'Advisory Fees', bu: 'Marsh', geo: 'APAC', variance: 6900, variancePct: 15.3, favorable: true, status: 'reviewed', assignedAnalyst: 'Sarah Chen', isEdited: true, varianceId: 'v1' },
  { id: 'ap2', account: 'Reinsurance Comm', bu: 'Guy Carpenter', geo: 'Americas', variance: 3300, variancePct: 9.4, favorable: true, status: 'approved', assignedAnalyst: 'Sarah Chen', isEdited: false, varianceId: 'v5' },
  { id: 'ap3', account: 'Data & Analytics', bu: 'Marsh', geo: 'Global', variance: 500, variancePct: 6.9, favorable: true, status: 'reviewed', assignedAnalyst: 'Sarah Chen', isEdited: false },
  { id: 'ap4', account: 'Investment Income', bu: 'MMC Corporate', geo: 'Global', variance: 800, variancePct: 4.9, favorable: true, status: 'approved', assignedAnalyst: 'Sarah Chen', isEdited: false },

  // James Park's items (4)
  { id: 'ap5', account: 'Tech Infrastructure', bu: 'All', geo: 'Global', variance: -5800, variancePct: -8.3, favorable: false, status: 'reviewed', assignedAnalyst: 'James Park', isEdited: true, varianceId: 'v2' },
  { id: 'ap6', account: 'Consulting Fees', bu: 'Oliver Wyman', geo: 'EMEA', variance: -4600, variancePct: -10.0, favorable: false, status: 'reviewed', assignedAnalyst: 'James Park', isEdited: false, varianceId: 'v3' },
  { id: 'ap7', account: 'Comp & Benefits', bu: 'Mercer', geo: 'Americas', variance: -3200, variancePct: -3.9, favorable: false, status: 'approved', assignedAnalyst: 'James Park', isEdited: false, varianceId: 'v4' },
  { id: 'ap8', account: 'Subcontractors', bu: 'Marsh', geo: 'UK', variance: -2100, variancePct: -5.4, favorable: false, status: 'approved', assignedAnalyst: 'James Park', isEdited: true },

  // Maria Santos's items (4)
  { id: 'ap9', account: 'Professional Svcs', bu: 'Oliver Wyman', geo: 'Americas', variance: 1200, variancePct: 3.8, favorable: true, status: 'reviewed', assignedAnalyst: 'Maria Santos', isEdited: false },
  { id: 'ap10', account: 'D&A', bu: 'Marsh', geo: 'Global', variance: 6000, variancePct: 12.5, favorable: true, status: 'approved', assignedAnalyst: 'Maria Santos', isEdited: false },
  { id: 'ap11', account: 'Occupancy', bu: 'Mercer', geo: 'EMEA', variance: 800, variancePct: 2.5, favorable: true, status: 'approved', assignedAnalyst: 'Maria Santos', isEdited: false },
  { id: 'ap12', account: 'T&E', bu: 'Guy Carpenter', geo: 'APAC', variance: -900, variancePct: -4.2, favorable: false, status: 'approved', assignedAnalyst: 'Maria Santos', isEdited: true },
]
