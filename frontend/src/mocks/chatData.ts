export interface MockChatResponse {
  text: string
  richContent: RichContent[]
  suggestions: string[]
}

export interface RichContent {
  type: 'confidence' | 'reviewStatus' | 'varianceCallout' | 'nettingAlert' | 'dataTable' | 'miniChart'
  data: any
}

export const INITIAL_SUGGESTIONS = ['Top variances?', 'Executive summary', 'Emerging risks?', 'EBITDA bridge?']

export const MOCK_RESPONSES: Record<string, MockChatResponse> = {
  revenue: {
    text: 'Revenue was $1,842K in June, +2.2% vs budget. Advisory strength in APAC (+15.3%) drove the beat, while EMEA consulting softness (-7.4%) partially offset gains. The net position remains favorable with strong pipeline visibility.',
    richContent: [
      { type: 'confidence', data: { score: 92, label: 'High' } },
      { type: 'reviewStatus', data: { approved: 3, draft: 2 } },
      { type: 'miniChart', data: { values: [1720,1780,1795,1803,1818,1842], color: '#2DD4A8', label: '6-month trend' } },
      { type: 'varianceCallout', data: { account: 'Advisory Fees', delta: '+15.3%', description: 'APAC new business acceleration', favorable: true, status: 'approved' } },
      { type: 'varianceCallout', data: { account: 'Consulting Fees', delta: '-7.4%', description: 'EMEA project delays', favorable: false, status: 'draft' } },
      { type: 'nettingAlert', data: { message: 'APAC revenue +0.4% masks $11.5M opposing movements (ratio 35.5x)' } },
      { type: 'dataTable', data: {
        columns: ['Account', 'Var', '%', 'Status'],
        rows: [
          ['Advisory Fees', '+$6.9K', '+15.3%', 'approved'],
          ['Consulting Fees', '-$4.6K', '-10.0%', 'draft'],
          ['Reinsurance', '+$3.3K', '+9.4%', 'approved'],
          ['Data & Analytics', '+$0.5K', '+6.9%', 'reviewed'],
        ]
      }}
    ],
    suggestions: ['Drill into Advisory APAC', 'Why is Consulting down?', 'Show netting detail', 'Export data']
  },
  ebitda: {
    text: 'EBITDA was $521K in June, +6.8% vs budget of $488K. The margin expanded to 28.3% from a planned 27.1%. Revenue outperformance and favorable OpEx (D&A timing) drove the beat.',
    richContent: [
      { type: 'confidence', data: { score: 88, label: 'High' } },
      { type: 'varianceCallout', data: { account: 'D&A', delta: '-$6.0K', description: 'Timing — Q2 catch-up expected', favorable: true, status: 'approved' } },
      { type: 'varianceCallout', data: { account: 'Technology', delta: '+$13.0K', description: '4th month above budget', favorable: false, status: 'reviewed' } },
    ],
    suggestions: ['Show EBITDA bridge', 'Tech cost trend detail', 'Compare to Q1', 'Board summary']
  },
  risk: {
    text: 'Two emerging risks flagged this period: (1) Technology infrastructure costs have been above budget for 4 consecutive months with a projected YE impact of +$580K. (2) EMEA consulting pipeline is 15% below target, suggesting Q3 softness.',
    richContent: [
      { type: 'confidence', data: { score: 78, label: 'Medium' } },
      { type: 'varianceCallout', data: { account: 'Tech Infrastructure', delta: '-8.3%', description: 'Cumulative trend — cloud migration', favorable: false, status: 'reviewed' } },
      { type: 'varianceCallout', data: { account: 'Consulting (EMEA)', delta: '-7.4%', description: 'Pipeline 15% below target', favorable: false, status: 'draft' } },
    ],
    suggestions: ['Tech cost breakdown', 'EMEA consulting detail', 'Mitigation options', 'Alert the team']
  },
  default: {
    text: 'I analyzed the current period data. Here is what I found across the material variances. Let me know if you would like me to drill into any specific area.',
    richContent: [
      { type: 'confidence', data: { score: 85, label: 'High' } },
      { type: 'dataTable', data: {
        columns: ['Metric', 'Actual', 'Budget', 'Variance'],
        rows: [
          ['Revenue', '$1,842K', '$1,803K', '+$39K'],
          ['COGS', '$612K', '$623K', '-$11K'],
          ['Gross Profit', '$1,230K', '$1,180K', '+$50K'],
          ['EBITDA', '$521K', '$488K', '+$33K'],
        ]
      }}
    ],
    suggestions: ['Revenue breakdown', 'Cost analysis', 'Show P&L', 'Top risks']
  }
}

// Intent matcher: match keywords in user message to response key
export function matchIntent(message: string): string {
  const lower = message.toLowerCase()
  if (lower.includes('revenue') || lower.includes('advisory') || lower.includes('top variance')) return 'revenue'
  if (lower.includes('ebitda') || lower.includes('bridge') || lower.includes('margin')) return 'ebitda'
  if (lower.includes('risk') || lower.includes('trend') || lower.includes('emerging')) return 'risk'
  if (lower.includes('summary') || lower.includes('executive') || lower.includes('overview')) return 'revenue'
  return 'default'
}
