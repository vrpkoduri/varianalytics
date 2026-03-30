import { useUser } from '@/context/UserContext'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'
import { PLGrid } from '@/components/pl/PLGrid'
import { MarginGaugesGrid } from '@/components/pl/MarginGaugesGrid'
import { MOCK_PL_DATA, MOCK_MARGINS } from '@/mocks/plData'

export default function PLView() {
  const { persona } = useUser()
  const { filters } = useGlobalFilters()

  const personaLabel: Record<string, string> = {
    analyst: 'FP&A Analyst',
    director: 'FP&A Director',
    cfo: 'CFO',
    bu: 'BU Leader',
  }
  void personaLabel

  const subtitle = `${filters.viewType} vs ${filters.comparisonBase}`

  return (
    <div className="space-y-3">
      <Breadcrumb title="P&L" subtitle={subtitle} />
      {persona === 'bu' && (
        <div
          className="px-3 py-1.5 rounded-lg text-[9px] animate-fade-up"
          style={{
            background: 'rgba(0,168,199,.06)',
            border: '1px solid rgba(0,168,199,.12)',
          }}
        >
          <span className="font-semibold text-teal">&#128274; Marsh</span>
          <span className="text-tx-secondary ml-1">
            Showing P&amp;L scoped to your business unit
          </span>
        </div>
      )}
      <PLGrid rows={MOCK_PL_DATA} />
      <MarginGaugesGrid margins={MOCK_MARGINS} />
      <MarshFooter />
    </div>
  )
}
