import { Badge } from '@/components/common/Badge'

interface NettingAlert {
  left: string
  right: string
  net: string
  favorable: boolean
}

interface TrendAlert {
  description: string
  projection: string
}

interface AlertCardsProps {
  persona: string
  nettingAlerts?: NettingAlert[]
  trendAlerts?: TrendAlert[]
}

const DEFAULT_NETTING_ALERTS: NettingAlert[] = [
  { left: 'T&E EMEA -$2.8K', right: 'T&E NAM +$2.1K', net: '-$0.7K', favorable: false },
  { left: 'Consulting Rev -$4.2K', right: 'Advisory Rev +$6.9K', net: '+$2.7K', favorable: true },
  { left: 'Real Estate -$2.2K', right: 'Outsourcing -$1.1K', net: '-$3.3K', favorable: false },
]

const DEFAULT_TREND_ALERTS: TrendAlert[] = [
  { description: 'Tech Infrastructure: 4th consecutive month above budget', projection: '+$580K YE' },
  { description: 'Cloud Services: trending 9% above plan since Mar', projection: '+$320K YE' },
]

export function AlertCards({ persona, nettingAlerts, trendAlerts }: AlertCardsProps) {
  // BU leaders don't see cross-BU netting alerts
  const showNetting = persona !== 'bu'
  const netting = nettingAlerts ?? DEFAULT_NETTING_ALERTS
  const trends = trendAlerts ?? DEFAULT_TREND_ALERTS

  return (
    <div className="grid grid-cols-1 tablet:grid-cols-2 gap-2.5 animate-fade-up d2">
      {showNetting && (
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="section-label" style={{ animation: 'borderPulse 2s ease infinite' }}>NETTING ALERTS</span>
            <Badge variant="purple">{netting.length} pairs</Badge>
          </div>
          <div className="space-y-2">
            {netting.map((alert, i) => (
              <div key={i} className="flex items-center justify-between text-[10px]">
                <span className="text-tx-secondary">{alert.left} &harr; {alert.right}</span>
                <span className={`${alert.favorable ? 'text-emerald' : alert.net.startsWith('+') ? 'text-emerald' : 'text-coral'} font-semibold`}>Net: {alert.net}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className={showNetting ? '' : 'col-span-full'}>
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="section-label" style={{ animation: 'borderPulse 2s ease infinite' }}>TREND ALERTS</span>
            <Badge variant="amber">{trends.length} trends</Badge>
          </div>
          <div className="space-y-2">
            {trends.map((alert, i) => (
              <div key={i} className="flex items-center justify-between text-[10px]">
                <span className="text-tx-secondary">{alert.description}</span>
                <span className="text-amber font-semibold">{alert.projection.toLowerCase().includes('projected') ? alert.projection : `Projected: ${alert.projection}`}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
