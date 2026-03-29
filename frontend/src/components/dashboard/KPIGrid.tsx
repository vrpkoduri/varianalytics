import { KPICard } from './KPICard'
import type { MockKPICard } from '@/mocks/dashboardData'

interface KPIGridProps {
  cards: MockKPICard[]
}

export function KPIGrid({ cards }: KPIGridProps) {
  return (
    <div className="grid grid-cols-2 tablet:grid-cols-5 gap-2.5 animate-fade-up d2">
      {cards.map((card) => (
        <KPICard key={card.id} card={card} />
      ))}
    </div>
  )
}
