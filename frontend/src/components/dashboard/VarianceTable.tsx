import React, { useState, useMemo } from 'react'
import { cn } from '@/utils/theme'
import { Badge } from '@/components/common/Badge'
import { InfoTooltip } from '@/components/common/Tooltip'
import { TOOLTIPS } from '@/mocks/tooltipContent'
import { SearchBar } from '@/components/common/SearchBar'
import { Sparkline } from '@/components/charts/Sparkline'
import { formatCurrency, formatPercent } from '@/utils/formatters'
import { useModal } from '@/context/ModalContext'
import { MOCK_MODAL_DATA } from '@/mocks/modalData'
import type { VarianceDetail } from '@/context/ModalContext'
import type { MockVariance } from '@/mocks/dashboardData'

type SortCol = 'account' | 'bu' | 'variance' | 'variancePct' | 'status'
type SortDir = 'asc' | 'desc'

interface VarianceTableProps {
  variances: MockVariance[]
  totalCount?: number
  searchQuery: string
  onSearchChange: (q: string) => void
}

const statusBadge: Record<string, { variant: 'emerald' | 'gold' | 'gray'; label: string }> = {
  approved: { variant: 'emerald', label: 'Approved' },
  reviewed: { variant: 'gold', label: 'Reviewed' },
  draft: { variant: 'gray', label: 'AI Draft' },
}

const typeBadge: Record<string, { variant: 'coral' | 'purple' | 'amber'; label: string }> = {
  material: { variant: 'coral', label: 'Material' },
  netted: { variant: 'purple', label: 'Netted' },
  trending: { variant: 'amber', label: 'Trending' },
}

const edgeBadgeVariant: Record<string, 'teal' | 'amber' | 'coral' | 'purple'> = {
  edited: 'teal',
  New: 'amber',
  'No budget': 'coral',
  synth: 'purple',
}

// Build a fallback VarianceDetail from a MockVariance row
function toVarianceDetail(v: MockVariance): VarianceDetail {
  return {
    id: v.id,
    account: v.account,
    bu: v.bu,
    geo: v.geo,
    variance: v.variance,
    variancePct: v.variancePct,
    favorable: v.favorable,
    type: v.type,
    status: v.status,
    sparkData: v.sparkData,
    decomposition: [],
    correlations: [],
    hypotheses: [],
    narratives: { detail: (v as any).narrativeDetail || v.narrative, midlevel: (v as any).narrativeDetail || v.narrative, summary: v.narrative, board: '' },
    isEdited: false,
    isSynthesized: false,
    isNew: v.edgeBadge === 'New',
    noBudget: v.edgeBadge === 'No budget',
    noPriorYear: false,
    edgeBadge: v.edgeBadge,
    narrative: v.narrative,
  }
}

export function VarianceTable({ variances, totalCount, searchQuery, onSearchChange }: VarianceTableProps) {
  const { openModal } = useModal()
  const [sortCol, setSortCol] = useState<SortCol>('variance')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const handleSort = (col: SortCol) => {
    if (sortCol === col) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortCol(col)
      setSortDir('desc')
    }
  }

  const filtered = useMemo(() => {
    let items = variances
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      items = items.filter(
        (v) =>
          v.account.toLowerCase().includes(q) ||
          v.bu.toLowerCase().includes(q) ||
          v.geo.toLowerCase().includes(q) ||
          v.narrative.toLowerCase().includes(q),
      )
    }
    return items
  }, [variances, searchQuery])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1
      switch (sortCol) {
        case 'account':
          return a.account.localeCompare(b.account) * dir
        case 'bu':
          return a.bu.localeCompare(b.bu) * dir
        case 'variance':
          return (Math.abs(a.variance) - Math.abs(b.variance)) * dir
        case 'variancePct':
          return (Math.abs(a.variancePct) - Math.abs(b.variancePct)) * dir
        case 'status': {
          const order = { approved: 3, reviewed: 2, draft: 1 }
          return ((order[a.status] ?? 0) - (order[b.status] ?? 0)) * dir
        }
        default:
          return 0
      }
    })
  }, [filtered, sortCol, sortDir])

  const SortArrow = ({ col }: { col: SortCol }) => (
    <span className="ml-0.5 text-[8px] text-tx-tertiary">
      {sortCol === col ? (sortDir === 'asc' ? '\u25B2' : '\u25BC') : '\u25BD'}
    </span>
  )

  return (
    <div className="glass-card p-4 animate-fade-up d4">
      <div className="flex items-center justify-between mb-3">
        <span className="section-label">MATERIAL VARIANCES</span>
        <InfoTooltip content={TOOLTIPS.materialVariances} />
        <div className="flex items-center gap-3">
          <span className="text-[9px] text-tx-tertiary">{sorted.length} items</span>
          <SearchBar
            value={searchQuery}
            onChange={onSearchChange}
            placeholder="Filter variances..."
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="sticky top-0 z-10" style={{ background: 'var(--surface)' }}>
            <tr className="border-b border-border">
              {([
                ['account', 'Account'],
                ['bu', 'BU'],
              ] as const).map(([col, label]) => (
                <th
                  key={col}
                  className="text-left text-[9px] text-tx-tertiary font-medium py-2 px-2 cursor-pointer hover:text-teal transition-colors"
                  onClick={() => handleSort(col)}
                >
                  {label}
                  <SortArrow col={col} />
                </th>
              ))}
              <th className="text-left text-[9px] text-tx-tertiary font-medium py-2 px-2">Geo</th>
              <th
                className="text-right text-[9px] text-tx-tertiary font-medium py-2 px-2 cursor-pointer hover:text-teal transition-colors"
                onClick={() => handleSort('variance')}
              >
                Variance
                <SortArrow col="variance" />
              </th>
              <th
                className="text-right text-[9px] text-tx-tertiary font-medium py-2 px-2 cursor-pointer hover:text-teal transition-colors"
                onClick={() => handleSort('variancePct')}
              >
                %
                <SortArrow col="variancePct" />
              </th>
              <th className="text-center text-[9px] text-tx-tertiary font-medium py-2 px-2">Trend</th>
              <th className="text-center text-[9px] text-tx-tertiary font-medium py-2 px-2">Type</th>
              <th
                className="text-center text-[9px] text-tx-tertiary font-medium py-2 px-2 cursor-pointer hover:text-teal transition-colors"
                onClick={() => handleSort('status')}
              >
                Status
                <SortArrow col="status" />
              </th>
              <th className="text-left text-[9px] text-tx-tertiary font-medium py-2 px-2 min-w-[200px]">
                Narrative
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((v) => {
              const sConf = statusBadge[v.status]
              const tConf = typeBadge[v.type]
              const isExpanded = expandedId === v.id
              return (
                <React.Fragment key={v.id}>
                  <tr
                    className="border-b border-border/50 border-l-[3px] border-l-transparent hover:border-l-teal hover:bg-[rgba(0,168,199,.03)] hover:shadow-sm cursor-pointer transition-all duration-150"
                    onClick={() => setExpandedId(isExpanded ? null : v.id)}
                  >
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-1.5">
                        <span className="text-table-sm text-tx-primary font-medium">
                          {v.account}
                        </span>
                        {v.edgeBadge && (
                          <Badge variant={edgeBadgeVariant[v.edgeBadge] ?? 'gray'} className="text-[7px] px-1 py-0">
                            {v.edgeBadge}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-2 px-2 text-table-sm text-tx-secondary">{v.bu}</td>
                    <td className="py-2 px-2 text-table-sm text-tx-secondary">{v.geo}</td>
                    <td className={cn('py-2 px-2 text-right text-table-var font-bold', v.favorable ? 'text-emerald' : 'text-coral')}>
                      {v.variance >= 0 ? '+' : ''}{formatCurrency(v.variance)}
                    </td>
                    <td className={cn('py-2 px-2 text-right text-table-sm', v.favorable ? 'text-emerald' : 'text-coral')}>
                      {formatPercent(v.variancePct)}
                    </td>
                    <td className="py-2 px-2 text-center">
                      <Sparkline
                        data={v.sparkData}
                        width={48}
                        height={14}
                        color={v.favorable ? '#2DD4A8' : '#F97066'}
                      />
                    </td>
                    <td className="py-2 px-2 text-center">
                      <Badge variant={tConf.variant}>{tConf.label}</Badge>
                    </td>
                    <td className="py-2 px-2 text-center">
                      <Badge variant={sConf.variant}>{sConf.label}</Badge>
                    </td>
                    <td className="py-2 px-2 text-[10px] text-tx-secondary leading-snug max-w-[260px] truncate">
                      {v.narrative}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={9} className="px-6 py-3 border-b border-border" style={{ background: 'rgba(0,168,199,.02)' }}>
                        <div className="text-[10px] text-tx-secondary leading-relaxed mb-2 pl-4">
                          {(v as any).narrativeDetail || v.narrative || 'No narrative available'}
                        </div>
                        {(v as any).narrativeSource === 'llm' && (
                          <span className="text-[7px] text-teal-400/60 ml-4 mb-1 inline-block">AI Agent Generated</span>
                        )}
                        <button
                          className="text-[8px] font-semibold px-3 py-1 rounded-md ml-4"
                          style={{ background: 'linear-gradient(135deg, var(--cobalt), var(--teal))', color: 'white' }}
                          onClick={(e) => { e.stopPropagation(); openModal(MOCK_MODAL_DATA[v.id] ?? toVarianceDetail(v)) }}
                        >
                          Detail &rarr;
                        </button>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-3 pt-2 border-t border-border">
        <span className="text-[9px] text-tx-tertiary">
          {sorted.length < (totalCount ?? variances.length)
            ? `Showing ${sorted.length} of ${totalCount ?? variances.length} variances`
            : `${totalCount ?? variances.length} variances`
          }
        </span>
        <div className="flex items-center gap-2">
          <button
            className="text-[9px] px-2 py-0.5 rounded-button border border-border text-tx-tertiary hover:border-teal hover:text-teal transition-colors"
            onClick={() => {
              const headers = ['Account', 'BU', 'Geo', 'Variance ($)', 'Variance (%)', 'Type', 'Status', 'Narrative']
              const csvRows = sorted.map(v => [
                v.account, v.bu, v.geo,
                v.variance, v.variancePct,
                v.type, v.status, `"${(v.narrative || '').replace(/"/g, '""')}"`
              ])
              const csv = [headers.join(','), ...csvRows.map(r => r.join(','))].join('\n')
              const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
              const url = URL.createObjectURL(blob)
              const link = document.createElement('a')
              link.href = url
              link.download = `variances_${new Date().toISOString().slice(0, 10)}.csv`
              link.click()
              URL.revokeObjectURL(url)
            }}
          >
            Export CSV
          </button>
          <button className="text-[9px] px-2 py-0.5 rounded-button border border-border text-tx-tertiary hover:border-teal hover:text-teal transition-colors">
            View All
          </button>
        </div>
      </div>
    </div>
  )
}
