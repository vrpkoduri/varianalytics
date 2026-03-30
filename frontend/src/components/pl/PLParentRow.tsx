import type { PLRowData } from '@/mocks/plData'
import { formatCurrency } from '@/utils/formatters'

interface PLParentRowProps {
  row: PLRowData
  isExpanded: boolean
  onToggle: () => void
  isEven?: boolean
}

export function PLParentRow({ row, isExpanded, onToggle, isEven }: PLParentRowProps) {
  const variance = row.actual - row.budget
  const variancePct = row.budget ? ((row.actual - row.budget) / Math.abs(row.budget)) * 100 : 0
  const isFavorable = row.signConvention === 'inverse' ? variance < 0 : variance > 0
  const isSmall = Math.abs(variancePct) < 2

  const varColor = isSmall
    ? 'var(--tx-tertiary)'
    : isFavorable
      ? 'var(--emerald)'
      : 'var(--coral)'

  return (
    <div
      className="grid items-center px-3 py-1.5 cursor-pointer transition-colors hover:bg-[rgba(0,168,199,.04)]"
      style={{
        gridTemplateColumns: 'minmax(230px, 2fr) 70px 70px 70px 65px 50px 50px',
        background: isEven ? 'rgba(0,168,199,.01)' : undefined,
      }}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onToggle() }}
    >
      <span className="text-[11px] font-semibold flex items-center gap-1.5" style={{ paddingLeft: '12px' }}>
        <span
          className="text-[9px] text-tx-tertiary inline-block"
          style={{
            transition: 'transform 0.2s cubic-bezier(.34,1.56,.64,1)',
            transform: isExpanded ? 'rotate(0deg)' : 'rotate(-90deg)',
            display: 'inline-block',
          }}
        >
          &#9662;
        </span>
        {row.name}
      </span>
      <span className="text-[10px] text-right font-display font-semibold">
        {formatCurrency(row.actual)}
      </span>
      <span className="text-[10px] text-right text-tx-secondary">
        {formatCurrency(row.budget)}
      </span>
      <span className="text-[10px] text-right font-semibold" style={{ color: varColor }}>
        {formatCurrency(variance)}
      </span>
      <span className="text-[10px] text-right" style={{ color: varColor }}>
        {variancePct >= 0 ? '+' : ''}{variancePct.toFixed(1)}%
      </span>
      <span className="text-center text-[10px]" />
      <span className="text-center text-[10px]" />
    </div>
  )
}
