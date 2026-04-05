export interface PLRowData {
  id: string
  name: string
  depth: number
  isContainer?: boolean
  children?: string[]
  isLeaf?: boolean
  parentId?: string
  isCalculated?: boolean
  isMajor?: boolean
  actual: number  // $K
  budget: number  // $K
  signConvention: 'normal' | 'inverse'
  status?: 'approved' | 'reviewed' | 'draft'
  type?: 'material' | 'trending' | 'netted'
  varianceId?: string
  narrativeDetail?: string
  narrativeOneliner?: string
  narrativeSource?: string
}

export interface MarginData {
  id: string
  label: string
  value: number
  delta: string
  color: string
}

export const MOCK_PL_DATA: PLRowData[] = [
  // --- Revenue ---
  {
    id: 'rev',
    name: 'Revenue',
    depth: 0,
    isContainer: true,
    children: ['rev-advisory', 'rev-consulting', 'rev-reinsurance', 'rev-investment', 'rev-data', 'rev-other'],
    actual: 52400,
    budget: 49800,
    signConvention: 'normal',
  },
  {
    id: 'rev-advisory',
    name: 'Advisory Fees',
    depth: 1,
    isLeaf: true,
    parentId: 'rev',
    actual: 18200,
    budget: 16800,
    signConvention: 'normal',
    status: 'approved',
    type: 'material',
    varianceId: 'v1',
  },
  {
    id: 'rev-consulting',
    name: 'Consulting Revenue',
    depth: 1,
    isLeaf: true,
    parentId: 'rev',
    actual: 12300,
    budget: 13100,
    signConvention: 'normal',
    status: 'draft',
    type: 'material',
    varianceId: 'v3',
  },
  {
    id: 'rev-reinsurance',
    name: 'Reinsurance Brokerage',
    depth: 1,
    isLeaf: true,
    parentId: 'rev',
    actual: 10600,
    budget: 9530,
    signConvention: 'normal',
    status: 'approved',
    type: 'material',
    varianceId: 'v5',
  },
  {
    id: 'rev-investment',
    name: 'Investment Income',
    depth: 1,
    isLeaf: true,
    parentId: 'rev',
    actual: 5800,
    budget: 5400,
    signConvention: 'normal',
  },
  {
    id: 'rev-data',
    name: 'Data & Analytics',
    depth: 1,
    isLeaf: true,
    parentId: 'rev',
    actual: 3900,
    budget: 3600,
    signConvention: 'normal',
  },
  {
    id: 'rev-other',
    name: 'Other Revenue',
    depth: 1,
    isLeaf: true,
    parentId: 'rev',
    actual: 1600,
    budget: 1370,
    signConvention: 'normal',
  },
  // --- GROSS REVENUE (calculated) ---
  {
    id: 'gross-rev',
    name: 'GROSS REVENUE',
    depth: 0,
    isCalculated: true,
    actual: 52400,
    budget: 49800,
    signConvention: 'normal',
  },
  // --- Cost of Revenue ---
  {
    id: 'cor',
    name: 'Cost of Revenue',
    depth: 0,
    isContainer: true,
    children: ['cor-comp', 'cor-sub', 'cor-tech', 'cor-other'],
    actual: 15400,
    budget: 14800,
    signConvention: 'inverse',
  },
  {
    id: 'cor-comp',
    name: 'Direct Compensation',
    depth: 1,
    isLeaf: true,
    parentId: 'cor',
    actual: 7800,
    budget: 7500,
    signConvention: 'inverse',
  },
  {
    id: 'cor-sub',
    name: 'Subcontractors',
    depth: 1,
    isLeaf: true,
    parentId: 'cor',
    actual: 3900,
    budget: 3700,
    signConvention: 'inverse',
  },
  {
    id: 'cor-tech',
    name: 'Direct Technology',
    depth: 1,
    isLeaf: true,
    parentId: 'cor',
    actual: 2400,
    budget: 2300,
    signConvention: 'inverse',
  },
  {
    id: 'cor-other',
    name: 'Other Direct Costs',
    depth: 1,
    isLeaf: true,
    parentId: 'cor',
    actual: 1300,
    budget: 1300,
    signConvention: 'inverse',
  },
  // --- TOTAL COR (calculated) ---
  {
    id: 'total-cor',
    name: 'TOTAL COR',
    depth: 0,
    isCalculated: true,
    actual: 15400,
    budget: 14800,
    signConvention: 'inverse',
  },
  // --- GROSS PROFIT (major) ---
  {
    id: 'gross-profit',
    name: 'GROSS PROFIT',
    depth: 0,
    isCalculated: true,
    isMajor: true,
    actual: 37000,
    budget: 35000,
    signConvention: 'normal',
  },
  // --- Operating Expenses ---
  {
    id: 'opex',
    name: 'Operating Expenses',
    depth: 0,
    isContainer: true,
    children: ['opex-comp', 'opex-tech', 'opex-prof', 'opex-occ', 'opex-te', 'opex-da', 'opex-other'],
    actual: 20800,
    budget: 20300,
    signConvention: 'inverse',
  },
  {
    id: 'opex-comp',
    name: 'Compensation & Benefits',
    depth: 1,
    isLeaf: true,
    parentId: 'opex',
    actual: 9500,
    budget: 9100,
    signConvention: 'inverse',
    status: 'reviewed',
    type: 'material',
    varianceId: 'v4',
  },
  {
    id: 'opex-tech',
    name: 'Technology',
    depth: 1,
    isLeaf: true,
    parentId: 'opex',
    actual: 4200,
    budget: 3880,
    signConvention: 'inverse',
    status: 'reviewed',
    type: 'trending',
    varianceId: 'v2',
  },
  {
    id: 'opex-prof',
    name: 'Professional Services',
    depth: 1,
    isLeaf: true,
    parentId: 'opex',
    actual: 2800,
    budget: 2900,
    signConvention: 'inverse',
  },
  {
    id: 'opex-occ',
    name: 'Occupancy',
    depth: 1,
    isLeaf: true,
    parentId: 'opex',
    actual: 1900,
    budget: 2000,
    signConvention: 'inverse',
  },
  {
    id: 'opex-te',
    name: 'Travel & Entertainment',
    depth: 1,
    isLeaf: true,
    parentId: 'opex',
    actual: 1200,
    budget: 1100,
    signConvention: 'inverse',
  },
  {
    id: 'opex-da',
    name: 'Depreciation & Amort.',
    depth: 1,
    isLeaf: true,
    parentId: 'opex',
    actual: 800,
    budget: 900,
    signConvention: 'inverse',
  },
  {
    id: 'opex-other',
    name: 'Other OpEx',
    depth: 1,
    isLeaf: true,
    parentId: 'opex',
    actual: 400,
    budget: 420,
    signConvention: 'inverse',
  },
  // --- TOTAL OPEX (calculated) ---
  {
    id: 'total-opex',
    name: 'TOTAL OPEX',
    depth: 0,
    isCalculated: true,
    actual: 20800,
    budget: 20300,
    signConvention: 'inverse',
  },
  // --- EBITDA (major) ---
  {
    id: 'ebitda',
    name: 'EBITDA',
    depth: 0,
    isCalculated: true,
    isMajor: true,
    actual: 16200,
    budget: 14700,
    signConvention: 'normal',
  },
  // --- OP INCOME (major) ---
  {
    id: 'op-income',
    name: 'OPERATING INCOME',
    depth: 0,
    isCalculated: true,
    isMajor: true,
    actual: 15000,
    budget: 13500,
    signConvention: 'normal',
  },
  // --- NET INCOME (major) ---
  {
    id: 'net-income',
    name: 'NET INCOME',
    depth: 0,
    isCalculated: true,
    isMajor: true,
    actual: 10750,
    budget: 9800,
    signConvention: 'normal',
  },
]

export const MOCK_MARGINS: MarginData[] = [
  { id: 'margin-gross', label: 'Gross Margin', value: 70.6, delta: '+0.6pp', color: 'var(--emerald)' },
  { id: 'margin-ebitda', label: 'EBITDA', value: 30.6, delta: '+1.3pp', color: 'var(--teal, #00A8C7)' },
  { id: 'margin-op', label: 'Op Margin', value: 28.3, delta: '+1.6pp', color: '#00A8C7' },
  { id: 'margin-tax', label: 'Tax Rate', value: 25.0, delta: '+0.1pp', color: 'var(--amber)' },
  { id: 'margin-net', label: 'Net Margin', value: 20.5, delta: '+1.2pp', color: 'var(--gold)' },
]
