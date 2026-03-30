import { Badge, type BadgeVariant } from '@/components/common/Badge'

interface InlineDataTableProps {
  columns: string[]
  rows: (string | number)[][]
}

const STATUS_BADGE: Record<string, BadgeVariant> = {
  approved: 'emerald',
  reviewed: 'gold',
  draft: 'gray',
}

function isStatusValue(val: string | number): val is string {
  return typeof val === 'string' && val in STATUS_BADGE
}

export function InlineDataTable({ columns, rows }: InlineDataTableProps) {
  const lastColIdx = columns.length - 1

  return (
    <div className="my-2 p-2.5 rounded-md bg-card border border-border text-[9px] overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="text-[7px] font-bold text-teal uppercase px-1.5 py-0.5 border-b border-border text-left"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} className="border-b border-border/50 last:border-0">
              {row.map((cell, ci) => (
                <td key={ci} className="px-1.5 py-1 text-tx-secondary">
                  {ci === lastColIdx && isStatusValue(cell) ? (
                    <Badge variant={STATUS_BADGE[cell]} className="text-[7px]">
                      {cell}
                    </Badge>
                  ) : (
                    cell
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
