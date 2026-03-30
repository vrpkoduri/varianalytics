import { useUser } from '@/context/UserContext'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { usePL } from '@/hooks/usePL'
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
        <Breadcrumb title="P&L" subtitle={subtitle} />
        <div className="glass-card p-4 h-96 animate-pulse" style={{ background: 'var(--glass)' }} />
        <div className="grid grid-cols-5 gap-2">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="glass-card p-4 h-20 animate-pulse"
              style={{ background: 'var(--glass)' }}
            />
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
          className="px-3 py-1 rounded text-[9px] text-tx-secondary"
          style={{
            background: 'rgba(255,191,0,.06)',
            border: '1px solid rgba(255,191,0,.15)',
          }}
        >
          Using cached data — backend unavailable
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
