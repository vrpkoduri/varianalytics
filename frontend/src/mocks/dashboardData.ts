// Mock data for the Marsh Vantage Dashboard

// KPI card shape
export interface MockKPICard {
  id: string
  label: string
  value: number
  prefix: string
  suffix: string
  delta: number
  favorable: boolean
  comparator: number
  comparatorLabel: string
  sparkData: number[]
}

export const MOCK_KPI_CARDS: MockKPICard[] = [
  { id: 'revenue', label: 'REVENUE', value: 1842, prefix: '$', suffix: 'K', delta: 2.2, favorable: true, comparator: 1803, comparatorLabel: 'vs $1,803K', sparkData: [1720, 1780, 1795, 1803, 1818, 1842] },
  { id: 'cogs', label: 'COGS', value: 612, prefix: '$', suffix: 'K', delta: -1.8, favorable: true, comparator: 623, comparatorLabel: 'vs $623K', sparkData: [640, 630, 625, 623, 618, 612] },
  { id: 'gross_profit', label: 'GROSS PROFIT', value: 1230, prefix: '$', suffix: 'K', delta: 4.1, favorable: true, comparator: 1182, comparatorLabel: 'vs $1,182K', sparkData: [1080, 1150, 1170, 1180, 1200, 1230] },
  { id: 'opex', label: 'OPEX', value: 742, prefix: '$', suffix: 'K', delta: 3.4, favorable: false, comparator: 718, comparatorLabel: 'vs $718K', sparkData: [700, 710, 715, 718, 730, 742] },
  { id: 'ebitda', label: 'EBITDA', value: 521, prefix: '$', suffix: 'K', delta: 6.8, favorable: true, comparator: 488, comparatorLabel: 'vs $488K', sparkData: [420, 450, 465, 488, 505, 521] },
]

// Waterfall step shape
export interface WaterfallStep {
  name: string
  value: number
  cumulative: number
  type: 'total' | 'positive' | 'negative'
}

export const MOCK_WATERFALL: WaterfallStep[] = [
  { name: 'Budget', value: 488, cumulative: 488, type: 'total' },
  { name: 'Advisory +$2.1K', value: 21, cumulative: 509, type: 'positive' },
  { name: 'Consulting -$0.8K', value: -8, cumulative: 501, type: 'negative' },
  { name: 'Reins +$0.6K', value: 6, cumulative: 507, type: 'positive' },
  { name: 'Comp -$1.2K', value: -12, cumulative: 495, type: 'negative' },
  { name: 'Tech +$1.8K', value: 18, cumulative: 513, type: 'positive' },
  { name: 'Other +$0.8K', value: 8, cumulative: 521, type: 'positive' },
  { name: 'Actual', value: 521, cumulative: 521, type: 'total' },
]

// Trend data shape
export interface TrendPoint {
  month: string
  actual: number
  budget: number
}

export const MOCK_TREND: TrendPoint[] = [
  { month: 'Jul', actual: 1720, budget: 1700 },
  { month: 'Aug', actual: 1740, budget: 1710 },
  { month: 'Sep', actual: 1780, budget: 1730 },
  { month: 'Oct', actual: 1795, budget: 1750 },
  { month: 'Nov', actual: 1803, budget: 1770 },
  { month: 'Dec', actual: 1810, budget: 1790 },
  { month: 'Jan', actual: 1790, budget: 1800 },
  { month: 'Feb', actual: 1805, budget: 1810 },
  { month: 'Mar', actual: 1818, budget: 1815 },
  { month: 'Apr', actual: 1803, budget: 1820 },
  { month: 'May', actual: 1818, budget: 1825 },
  { month: 'Jun', actual: 1842, budget: 1830 },
]

// Heatmap shape
export interface HeatmapData {
  columns: string[]
  rows: { bu: string; cells: number[] }[]
}

export const MOCK_HEATMAP: HeatmapData = {
  columns: ['Rev', 'COGS', 'Comp', 'Tech', 'T&E'],
  rows: [
    { bu: 'Marsh', cells: [3.2, -1.4, 2.1, -4.2, 1.8] },
    { bu: 'Mercer', cells: [-1.1, 0.8, -0.5, 2.3, -3.1] },
    { bu: 'Guy Carpenter', cells: [2.8, -2.1, 1.5, 0.3, -0.7] },
    { bu: 'Oliver Wyman', cells: [-2.5, 1.2, -1.8, 5.1, 2.2] },
    { bu: 'MMC Corporate', cells: [0.4, -0.3, 0.8, -1.5, 0.2] },
  ],
}

// Variance row shape
export interface MockVariance {
  id: string
  account: string
  bu: string
  geo: string
  variance: number
  variancePct: number
  favorable: boolean
  sparkData: number[]
  type: 'material' | 'netted' | 'trending'
  status: 'approved' | 'reviewed' | 'draft'
  edgeBadge?: 'edited' | 'New' | 'No budget' | 'synth'
  narrative: string
}

export const MOCK_VARIANCES: MockVariance[] = [
  { id: 'v1', account: 'Advisory Fees', bu: 'Marsh', geo: 'APAC', variance: 6900, variancePct: 15.3, favorable: true, sparkData: [4, 5, 6, 5, 7, 8], type: 'material', status: 'approved', edgeBadge: 'edited', narrative: 'APAC advisory drives upside on strong client wins in Q2.' },
  { id: 'v2', account: 'Tech Infrastructure', bu: 'All', geo: 'Global', variance: -5800, variancePct: -8.3, favorable: false, sparkData: [1, 2, 3, 4, 5, 6], type: 'trending', status: 'reviewed', narrative: 'Tech costs above budget due to cloud migration acceleration.' },
  { id: 'v3', account: 'Consulting Revenue', bu: 'Oliver Wyman', geo: 'EMEA', variance: -4200, variancePct: -6.1, favorable: false, sparkData: [8, 7, 6, 5, 4, 3], type: 'material', status: 'draft', narrative: 'EMEA consulting pipeline delays impacting revenue recognition.' },
  { id: 'v4', account: 'Compensation', bu: 'Mercer', geo: 'NAM', variance: -3500, variancePct: -4.8, favorable: false, sparkData: [3, 4, 5, 5, 6, 7], type: 'material', status: 'reviewed', narrative: 'Headcount additions in NAM wealth management practice.' },
  { id: 'v5', account: 'Reinsurance Brokerage', bu: 'Guy Carpenter', geo: 'Global', variance: 5100, variancePct: 11.2, favorable: true, sparkData: [5, 5, 6, 7, 8, 9], type: 'material', status: 'approved', narrative: 'Strong Jan 1 renewal season and cat bond placements.' },
  { id: 'v6', account: 'Travel & Entertainment', bu: 'Marsh', geo: 'EMEA', variance: -2800, variancePct: -12.5, favorable: false, sparkData: [2, 3, 4, 5, 6, 7], type: 'netted', status: 'draft', narrative: 'EMEA conference season spending above plan; partially offset by NAM savings.' },
  { id: 'v7', account: 'Benefits Admin Fees', bu: 'Mercer', geo: 'APAC', variance: 3200, variancePct: 8.7, favorable: true, sparkData: [4, 4, 5, 6, 7, 7], type: 'material', status: 'approved', narrative: 'New client onboarding in Australia and Japan benefits platforms.' },
  { id: 'v8', account: 'Cloud Services', bu: 'All', geo: 'Global', variance: -4100, variancePct: -9.2, favorable: false, sparkData: [2, 3, 4, 5, 6, 8], type: 'trending', status: 'reviewed', edgeBadge: 'synth', narrative: 'Azure consumption trending 9% above plan. 4th consecutive month.' },
  { id: 'v9', account: 'Professional Fees', bu: 'MMC Corporate', geo: 'NAM', variance: -1900, variancePct: -5.4, favorable: false, sparkData: [3, 3, 4, 4, 5, 5], type: 'material', status: 'draft', narrative: 'Legal advisory fees for M&A due diligence.' },
  { id: 'v10', account: 'Specialty Lines', bu: 'Marsh', geo: 'NAM', variance: 4500, variancePct: 9.8, favorable: true, sparkData: [5, 6, 6, 7, 8, 9], type: 'material', status: 'approved', narrative: 'Cyber and environmental specialty growth exceeds plan.' },
  { id: 'v11', account: 'Investment Income', bu: 'All', geo: 'Global', variance: 2100, variancePct: 18.4, favorable: true, sparkData: [3, 4, 5, 6, 7, 8], type: 'material', status: 'reviewed', edgeBadge: 'New', narrative: 'Higher interest rates on fiduciary balances.' },
  { id: 'v12', account: 'Depreciation', bu: 'All', geo: 'Global', variance: -1200, variancePct: -3.1, favorable: false, sparkData: [4, 4, 5, 5, 5, 6], type: 'netted', status: 'draft', narrative: 'Accelerated depreciation on legacy systems being retired.' },
  { id: 'v13', account: 'Health Consulting', bu: 'Mercer', geo: 'EMEA', variance: 2800, variancePct: 7.3, favorable: true, sparkData: [4, 5, 5, 6, 7, 7], type: 'material', status: 'approved', narrative: 'UK health consulting mandates above plan on NHS reform.' },
  { id: 'v14', account: 'Marketing Spend', bu: 'Oliver Wyman', geo: 'NAM', variance: -1500, variancePct: -22.1, favorable: false, sparkData: [2, 3, 4, 5, 7, 8], type: 'trending', status: 'draft', edgeBadge: 'No budget', narrative: 'Brand refresh campaign costs. No budget line established.' },
  { id: 'v15', account: 'Facultative Reins', bu: 'Guy Carpenter', geo: 'APAC', variance: 1800, variancePct: 6.5, favorable: true, sparkData: [5, 5, 6, 6, 7, 7], type: 'material', status: 'reviewed', narrative: 'APAC facultative placements above plan on Japan earthquake demand.' },
  { id: 'v16', account: 'Real Estate', bu: 'MMC Corporate', geo: 'Global', variance: -2200, variancePct: -4.7, favorable: false, sparkData: [4, 4, 5, 5, 6, 6], type: 'netted', status: 'approved', narrative: 'Lease renegotiation savings offset by fit-out costs in London.' },
  { id: 'v17', account: 'Data & Analytics', bu: 'Marsh', geo: 'Global', variance: 3800, variancePct: 13.6, favorable: true, sparkData: [3, 4, 5, 6, 7, 9], type: 'material', status: 'reviewed', edgeBadge: 'edited', narrative: 'Sentrisk and data analytics product revenue exceeding targets.' },
  { id: 'v18', account: 'Outsourcing', bu: 'Mercer', geo: 'NAM', variance: -1100, variancePct: -2.9, favorable: false, sparkData: [5, 5, 5, 5, 6, 6], type: 'netted', status: 'draft', narrative: 'BPO contract costs slightly above plan on volume increases.' },
  { id: 'v19', account: 'Carrier Relations', bu: 'Marsh', geo: 'LATAM', variance: 1400, variancePct: 5.2, favorable: true, sparkData: [4, 5, 5, 6, 6, 7], type: 'material', status: 'approved', narrative: 'LATAM placement revenue up on market hardening.' },
  { id: 'v20', account: 'Restructuring', bu: 'Oliver Wyman', geo: 'Global', variance: -3100, variancePct: -7.8, favorable: false, sparkData: [2, 3, 4, 5, 6, 7], type: 'material', status: 'reviewed', narrative: 'Restructuring advisory project delays pushing revenue into Q3.' },
]

// Executive summary narratives per persona
export const MOCK_EXEC_SUMMARIES: Record<string, string> = {
  analyst: '<b>June close: Revenue +2.2%, EBITDA +6.8%.</b> Advisory strength in APAC (+15.3%) offset by EMEA consulting softness. Tech trend continues \u2014 4th consecutive month above budget.',
  director: '<b>June close: Revenue +2.2%, EBITDA +6.8%.</b> Strong advisory offset by EMEA consulting. 12 of 25 material variances approved. 3 need attention.',
  cfo: '<b>Q2 revenue $1,842K, +2.2% vs budget. EBITDA 28.3% vs 27.1% plan.</b> Advisory outperformance, consulting risk in EMEA. Tech trend projected +$580K YE.',
  bu: '<b>Marsh June: Advisory +15.3% APAC, strong pipeline.</b> Consulting -2.1% EMEA, seasonal. Tech +$1.8K above plan.',
}

// Success metrics
export interface MockMetrics {
  cycleTime: number
  coverage: number
  rootCause: number
  commentary: number
}

export const MOCK_METRICS: MockMetrics = { cycleTime: 18, coverage: 100, rootCause: 81, commentary: 92 }
