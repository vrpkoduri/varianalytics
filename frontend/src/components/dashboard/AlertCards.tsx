import { Badge } from '@/components/common/Badge'

interface AlertCardsProps {
  persona: string
}

export function AlertCards({ persona }: AlertCardsProps) {
  // BU leaders don't see cross-BU netting alerts
  const showNetting = persona !== 'bu'

  return (
    <div className="grid grid-cols-1 tablet:grid-cols-2 gap-2.5 animate-fade-up d2">
      {showNetting && (
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="section-label">NETTING ALERTS</span>
            <Badge variant="purple">3 pairs</Badge>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-tx-secondary">T&amp;E EMEA -$2.8K &harr; T&amp;E NAM +$2.1K</span>
              <span className="text-purple font-semibold">Net: -$0.7K</span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-tx-secondary">Consulting Rev -$4.2K &harr; Advisory Rev +$6.9K</span>
              <span className="text-emerald font-semibold">Net: +$2.7K</span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-tx-secondary">Real Estate -$2.2K &harr; Outsourcing -$1.1K</span>
              <span className="text-coral font-semibold">Net: -$3.3K</span>
            </div>
          </div>
        </div>
      )}

      <div className={showNetting ? '' : 'col-span-full'}>
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="section-label">TREND ALERTS</span>
            <Badge variant="amber">2 trends</Badge>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-tx-secondary">Tech Infrastructure: 4th consecutive month above budget</span>
              <span className="text-amber font-semibold">Projected: +$580K YE</span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-tx-secondary">Cloud Services: trending 9% above plan since Mar</span>
              <span className="text-amber font-semibold">Projected: +$320K YE</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
