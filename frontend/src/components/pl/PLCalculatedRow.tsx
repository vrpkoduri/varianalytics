import type { PLRowData } from '@/mocks/plData'
import { formatCurrency } from '@/utils/formatters'

interface PLCalculatedRowProps {
  row: PLRowData
}

export function PLCalculatedRow({ row }: PLCalculatedRowProps) {
  const variance = row.actual - row.budget
  const variancePct = row.budget ? ((row.actual - row.budget) / Math.abs(row.budget)) * 100 : 0
  const isFavorable = row.signConvention === 'inverse' ? variance < 0 : variance > 0
  const isSmall = Math.abs(variancePct) < 2

  const varColor = isSmall
    ? 'var(--tx-tertiary)'
    : isFavorable
      ? 'var(--emerald)'
      : 'var(--coral)'

  const isMajor = row.isMajor

  return (
    <div
      className="grid items-center px-3 py-1.5"
      style={{
        gridTemplateColumns: 'minmax(230px, 2fr) 70px 70px 70px 65px 50px 50px',
        background: isMajor
          ? 'linear-gradient(90deg, rgba(0,168,199,.04), transparent)'
          : 'var(--card-alt)',
        borderBottom: isMajor
          ? '2px solid rgba(0,168,199,.15)'
          : '1px solid var(--border)',
      }}
    >
      <span
        className={
          isMajor
            ? 'font-display font-bold text-[11px] text-teal'
            : 'text-[11px] font-semibold'
        }
        style={{ paddingLeft: '12px' }}
      >
        {row.name}
      </span>
      <span
        className={
          isMajor
            ? 'text-right font-display font-bold text-teal text-[11px]'
            : 'text-[10px] text-right font-display font-semibold'
        }
      >
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
