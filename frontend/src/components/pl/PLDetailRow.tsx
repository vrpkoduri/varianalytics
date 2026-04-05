import type { PLRowData } from '@/mocks/plData'
import { Badge } from '@/components/common/Badge'
import { formatCurrency } from '@/utils/formatters'

interface PLDetailRowProps {
  row: PLRowData
  onOpenModal: () => void
  isEven?: boolean
}

const typeToBadgeVariant = {
  material: 'coral' as const,
  trending: 'amber' as const,
  netted: 'purple' as const,
}

export function PLDetailRow({ row, onOpenModal, isEven }: PLDetailRowProps) {
  const variance = row.actual - row.budget
  const variancePct = row.budget ? ((row.actual - row.budget) / Math.abs(row.budget)) * 100 : 0
  const isFavorable = row.signConvention === 'inverse' ? variance < 0 : variance > 0
  const isSmall = Math.abs(variancePct) < 2
  const isSignificant = Math.abs(variancePct) > 5

  const varColor = isSmall
    ? 'var(--tx-tertiary)'
    : isFavorable
      ? 'var(--emerald)'
      : 'var(--coral)'

  // E5: Heat coloring based on variance magnitude
  const intensity = Math.min(Math.abs(variancePct) / 10, 1) * 0.06
  const heatBg = Math.abs(variancePct) > 2
    ? (isFavorable ? `rgba(45,212,168,${intensity})` : `rgba(249,112,102,${intensity})`)
    : undefined

  return (
    <div
      className="grid items-center px-3 py-1 cursor-pointer transition-colors hover:bg-[rgba(0,168,199,.05)]"
      style={{
        gridTemplateColumns: 'minmax(180px, 1fr) 70px 70px 70px 60px 45px 50px',
        background: heatBg || (isEven ? 'rgba(0,168,199,.01)' : undefined),
      }}
      onClick={onOpenModal}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onOpenModal() }}
    >
      <span className="text-[10px] font-normal flex items-center gap-1.5" style={{ paddingLeft: '34px' }}>
        {isSignificant && (
          <span
            className="inline-block w-[5px] h-[5px] rounded-full flex-shrink-0"
            style={{ background: varColor }}
          />
        )}
        {row.name}
      </span>
      <span className="text-[10px] text-right font-body">
        {formatCurrency(row.actual)}
      </span>
      <span className="text-[10px] text-right text-tx-secondary">
        {formatCurrency(row.budget)}
      </span>
      <span className="text-[10px] text-right font-semibold" style={{ color: varColor }}>
        {formatCurrency(variance)}
      </span>
      <span className="text-right">
        {isSignificant ? (
          <span
            className="inline-block text-[9px] font-semibold px-1.5 py-0.5 rounded-full"
            style={{
              background: isFavorable ? 'var(--emerald-surface)' : 'var(--coral-surface)',
              color: varColor,
            }}
          >
            {variancePct >= 0 ? '+' : ''}{variancePct.toFixed(1)}%
          </span>
        ) : (
          <span className="text-[10px]" style={{ color: varColor }}>
            {variancePct >= 0 ? '+' : ''}{variancePct.toFixed(1)}%
          </span>
        )}
      </span>
      <span className="text-center text-[10px]">
        {!isSmall && (
          isFavorable
            ? <span style={{ color: 'var(--emerald)' }}>&#10003;</span>
            : <span style={{ color: 'var(--coral)' }}>&#10007;</span>
        )}
      </span>
      <span className="text-center">
        {row.type && (
          <Badge variant={typeToBadgeVariant[row.type]}>
            {row.type.charAt(0).toUpperCase() + row.type.slice(1)}
          </Badge>
        )}
      </span>
    </div>
  )
}
