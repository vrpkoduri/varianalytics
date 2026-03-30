import { KPICard } from './KPICard'
import type { MockKPICard } from '@/mocks/dashboardData'

interface KPIGridProps {
  cards: MockKPICard[]
}

export function KPIGrid({ cards }: KPIGridProps) {
  // Limit to 5 cards max to fit the 5-column grid layout
  const displayCards = cards.slice(0, 5)

  return (
    <div className="grid grid-cols-2 tablet:grid-cols-5 gap-2.5 animate-fade-up d2">
      {displayCards.map((card) => (
        <KPICard key={card.id} card={card} />
      ))}
    </div>
  )
}
