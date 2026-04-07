import { useState, useMemo } from 'react'
import type { PLRowData } from '@/mocks/plData'
import { MOCK_MODAL_DATA } from '@/mocks/modalData'
import { useModal, type VarianceDetail } from '@/context/ModalContext'
import { GlassCard } from '@/components/common/GlassCard'
import { SectionLabel } from '@/components/common/SectionLabel'
import { PLHeaderRow } from './PLHeaderRow'
import { PLParentRow } from './PLParentRow'
import { PLDetailRow } from './PLDetailRow'
import { PLCalculatedRow } from './PLCalculatedRow'

interface PLGridProps {
  rows: PLRowData[]
}

export function PLGrid({ rows }: PLGridProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    () => new Set(['rev', 'cor', 'opex']),
  )
  const { openModal } = useModal()

  const containerIds = useMemo(
    () => rows.filter((r) => r.isContainer).map((r) => r.id),
    [rows],
  )

  const allExpanded = containerIds.every((id) => expandedIds.has(id))

  function toggleId(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  function expandAll() {
    setExpandedIds(new Set(containerIds))
  }

  function collapseAll() {
    setExpandedIds(new Set())
  }

  function handleLeafClick(row: PLRowData) {
    // Try preloaded modal data first
    if (row.varianceId && MOCK_MODAL_DATA[row.varianceId]) {
      openModal(MOCK_MODAL_DATA[row.varianceId])
      return
    }

    // Build a basic VarianceDetail from the row itself
    const variance = row.actual - row.budget
    const detail: VarianceDetail = {
      id: row.id,
      account: row.name,
      bu: 'All',
      geo: 'Global',
      variance: variance * 1000, // Convert back from $K
      variancePct: row.budget ? (variance / Math.abs(row.budget)) * 100 : 0,
      favorable: row.signConvention === 'inverse' ? variance < 0 : variance > 0,
      type: row.type || 'material',
      status: row.status || 'draft',
      sparkData: [],
      decomposition: [],
      correlations: [],
      hypotheses: [],
      narratives: {
        detail: (row as any).narrativeDetail || `${row.name}: $${Math.abs(variance)}K variance`,
        midlevel: (row as any).narrativeDetail || '',
        summary: (row as any).narrativeOneliner || '',
        board: '',
      },
      isEdited: false,
      isSynthesized: false,
      isNew: false,
      noBudget: row.budget === 0,
      noPriorYear: false,
      narrative: '',
    }
    openModal(detail)
  }

  let visibleIndex = 0

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between mb-2">
        <SectionLabel>Income Statement</SectionLabel>
        <div className="flex gap-2">
          <button
            className="text-[8px] font-semibold text-teal uppercase tracking-[0.5px] px-2 py-0.5 rounded hover:bg-[rgba(0,168,199,.08)] transition-colors"
            onClick={allExpanded ? collapseAll : expandAll}
          >
            {allExpanded ? 'Collapse All' : 'Expand All'}
          </button>
          {/* Compare mode stub — Sprint 2 */}
          <button
            className="text-[8px] px-2 py-0.5 rounded-md border"
            style={{ borderColor: 'var(--border)', color: 'var(--tx-tertiary)' }}
            title="Compare MTD vs QTD (coming soon)"
            disabled
          >
            Compare
          </button>
        </div>
      </div>
      <GlassCard className="overflow-x-auto">
        <PLHeaderRow />
        <div>
          {rows.map((row) => {
            // Calculated rows always visible
            if (row.isCalculated) {
              return <PLCalculatedRow key={row.id} row={row} />
            }

            // Container rows always visible
            if (row.isContainer) {
              const isEven = visibleIndex % 2 === 0
              visibleIndex++
              return (
                <PLParentRow
                  key={row.id}
                  row={row}
                  isExpanded={expandedIds.has(row.id)}
                  onToggle={() => toggleId(row.id)}
                  isEven={isEven}
                />
              )
            }

            // Leaf rows visible only if parent expanded
            if (row.isLeaf && row.parentId && expandedIds.has(row.parentId)) {
              const isEven = visibleIndex % 2 === 0
              visibleIndex++
              return (
                <PLDetailRow
                  key={row.id}
                  row={row}
                  onOpenModal={() => handleLeafClick(row)}
                  isEven={isEven}
                />
              )
            }

            return null
          })}
        </div>
      </GlassCard>
    </div>
  )
}
