import { cn } from '@/utils/theme'
import { InfoTooltip } from '@/components/common/Tooltip'
import { TOOLTIPS } from '@/mocks/tooltipContent'
import type { HeatmapData } from '@/mocks/dashboardData'

interface HeatmapProps {
  data: HeatmapData
  activeFilter: { bu: string; cat: string } | null
  onCellClick: (filter: { bu: string; cat: string } | null) => void
  persona: string
}

function getCellColor(value: number): string {
  if (value > 3) return 'bg-emerald/20 text-emerald'
  if (value > 1) return 'bg-emerald/10 text-emerald'
  if (value > 0) return 'bg-emerald/5 text-emerald'
  if (value > -1) return 'bg-coral/5 text-coral'
  if (value > -3) return 'bg-coral/10 text-coral'
  return 'bg-coral/20 text-coral'
}

export function Heatmap({ data, activeFilter, onCellClick, persona }: HeatmapProps) {
  // BU leaders only see their own BU row
  const rows = persona === 'bu'
    ? data.rows.filter((r) => r.bu === 'Marsh')
    : data.rows

  // Empty state
  if (!data.rows || data.rows.length === 0 || !data.columns || data.columns.length === 0) {
    return (
      <div className="glass-card p-4 animate-fade-up d3">
        <div className="section-label mb-3">VARIANCE HEATMAP</div>
        <div className="flex items-center justify-center text-tx-tertiary text-body-md h-[120px]">
          No data for this period
        </div>
      </div>
    )
  }

  return (
    <div className="glass-card p-4 animate-fade-up d3">
      <div className="flex items-center justify-between mb-3">
        <span className="section-label">VARIANCE HEATMAP</span>
        <InfoTooltip content={TOOLTIPS.heatmap} />
        {activeFilter && (
          <button
            onClick={() => onCellClick(null)}
            className="text-[9px] text-teal hover:text-teal-light transition-colors"
          >
            Clear filter: {activeFilter.bu} / {activeFilter.cat}
          </button>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr>
              <th className="text-left text-[9px] text-tx-tertiary font-medium py-1 px-2 w-[120px]">BU</th>
              {data.columns.map((col) => (
                <th key={col} className="text-center text-[9px] text-tx-tertiary font-medium py-1 px-2">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.bu}>
                <td className="text-[10px] text-tx-secondary font-medium py-1 px-2">{row.bu}</td>
                {row.cells.map((cell, ci) => {
                  const isActive =
                    activeFilter?.bu === row.bu && activeFilter?.cat === data.columns[ci]
                  return (
                    <td key={ci} className="py-1 px-1">
                      <button
                        onClick={() =>
                          onCellClick(
                            isActive ? null : { bu: row.bu, cat: data.columns[ci] },
                          )
                        }
                        className={cn(
                          'w-full py-1.5 rounded text-[10px] font-semibold text-center transition-all duration-150',
                          getCellColor(cell),
                          isActive && 'ring-2 ring-teal ring-offset-1 ring-offset-[var(--card)]',
                          'hover:scale-[1.02] hover:shadow-[inset_0_0_12px_rgba(255,255,255,.08)] hover:z-10 cursor-pointer',
                        )}
                      >
                        {cell > 0 ? '+' : ''}{cell.toFixed(1)}%
                      </button>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
