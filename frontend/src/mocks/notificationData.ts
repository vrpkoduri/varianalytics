export interface NotificationItem {
  id: string
  text: string
  time: string
  read: boolean
  type: 'info' | 'warning' | 'success'
}

export const MOCK_NOTIFICATIONS: NotificationItem[] = [
  { id: 'n1', text: 'Engine run complete — 25 material variances identified', time: '18 min ago', read: false, type: 'info' },
  { id: 'n2', text: 'Sarah Chen reviewed 3 variances in Advisory', time: '42 min ago', read: false, type: 'success' },
  { id: 'n3', text: 'SLA warning: Tech Infrastructure pending >24h', time: '1h ago', read: false, type: 'warning' },
  { id: 'n4', text: 'James Park escalated Consulting EMEA variance', time: '2h ago', read: true, type: 'warning' },
  { id: 'n5', text: 'Q2 Board Package draft generated', time: '3h ago', read: true, type: 'info' },
  { id: 'n6', text: 'Weekly Pulse report distributed to 12 recipients', time: '1d ago', read: true, type: 'success' },
  { id: 'n7', text: 'Forecast data refreshed for Jul-Dec 2026', time: '2d ago', read: true, type: 'info' },
]
