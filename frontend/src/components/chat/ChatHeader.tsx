import { INITIAL_SUGGESTIONS } from '@/mocks/chatData'
import { SuggestionPills } from './SuggestionPills'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'

interface ChatHeaderProps {
  persona: string
  viewType: string
  comparisonBase: string
  hasMessages: boolean
  onSuggestionSelect: (text: string) => void
}

const PERSONA_GREETINGS: Record<string, string> = {
  analyst: 'Ready to analyze variances at detail level',
  director: 'Showing midlevel summaries for your review',
  cfo: 'Executive summary view — approved items only',
  bu: 'Focused on your business unit variances',
}

export function ChatHeader({ persona, viewType, comparisonBase, hasMessages, onSuggestionSelect }: ChatHeaderProps) {
  // E14: Show active BU filter context
  const { filters } = useGlobalFilters()

  return (
    <div className="text-center p-5">
      <h2 className="font-display text-[22px] font-bold text-tx-primary">
        Marsh Vantage
      </h2>
      <p className="text-[10px] text-tx-tertiary mt-1">
        {PERSONA_GREETINGS[persona] || PERSONA_GREETINGS.analyst}
      </p>
      <span className="text-[8px] bg-card-alt rounded-md inline-block px-2.5 py-0.5 mt-2 text-tx-secondary">
        {viewType} vs {comparisonBase}
      </span>
      {filters.businessUnit && (
        <div
          className="text-[8px] mt-1 px-2.5 py-0.5 rounded-md inline-block"
          style={{ background: 'rgba(0,168,199,.1)', border: '1px solid rgba(0,168,199,.15)', color: 'var(--teal)' }}
        >
          Analyzing: {filters.businessUnit.replace(/_/g, ' ')}
        </div>
      )}

      {!hasMessages && (
        <div className="mt-4">
          <SuggestionPills pills={INITIAL_SUGGESTIONS} onSelect={onSuggestionSelect} />
        </div>
      )}
    </div>
  )
}
