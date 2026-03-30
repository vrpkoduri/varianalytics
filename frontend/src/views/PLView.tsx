import { useUser } from '@/context/UserContext'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { usePL } from '@/hooks/usePL'
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'
import { PLGrid } from '@/components/pl/PLGrid'
import { MarginGaugesGrid } from '@/components/pl/MarginGaugesGrid'

export default function PLView() {
  const { persona } = useUser()
  const { filters } = useGlobalFilters()
  const { rows, margins, loading, usingMock } = usePL()

  const subtitle = `${filters.viewType} vs ${filters.comparisonBase}`

  if (loading) {
    return (
      <div className="space-y-3">
        <LoadingSkeleton height="30px" width="120px" />
        <LoadingSkeleton height="380px" />
        <div className="grid grid-cols-5 gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <LoadingSkeleton key={i} height="80px" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <Breadcrumb title="P&L" subtitle={subtitle} />

      {usingMock && (
        <div
          className="px-3 py-1 rounded-md text-[8px] font-semibold mb-2 animate-fade-up"
          style={{ background: 'rgba(251,191,36,.06)', border: '1px solid rgba(251,191,36,.12)', color: 'var(--amber)' }}
        >
          Warning: Using cached data — backend unavailable
        </div>
      )}

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
      <PLGrid rows={rows} />
      <MarginGaugesGrid margins={margins} />
      <MarshFooter />
    </div>
  )
}
