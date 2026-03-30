import { useState, useCallback } from 'react'
import { DonutProgress } from '../sidebar/DonutProgress'
import { BUList } from '../sidebar/BUList'
import { HierarchyTree } from '../sidebar/HierarchyTree'
import { useDimensions } from '../../hooks/useDimensions'
import { useGlobalFilters } from '../../context/GlobalFiltersContext'
import { cn } from '@/utils/theme'

// Dimension display labels
const DIMENSION_LABELS: Record<string, string> = {
  geography: 'Geography',
  segment: 'Segment',
  lob: 'Line of Business',
  costcenter: 'Cost Center',
}

// ── Component ────────────────────────────────────────────────────────

interface SidebarProps {
  isOpen: boolean
}

export default function Sidebar({ isOpen }: SidebarProps) {
  const { businessUnits, hierarchies } = useDimensions()
  const { filters, setBusinessUnit, setDimensionFilter } = useGlobalFilters()

  // Tree expanded/active state per dimension
  const [expandedMap, setExpandedMap] = useState<Record<string, Set<string>>>({
    geography: new Set(['global']),
    segment: new Set(['all_seg']),
    lob: new Set(['all_lob']),
    costcenter: new Set(['all_cc']),
  })
  const [activeMap, setActiveMap] = useState<Record<string, string | null>>({
    geography: null,
    segment: null,
    lob: null,
    costcenter: null,
  })

  const makeToggle = useCallback(
    (dim: string) => (id: string) => {
      setExpandedMap((prev) => {
        const next = new Set(prev[dim] || new Set())
        if (next.has(id)) next.delete(id)
        else next.add(id)
        return { ...prev, [dim]: next }
      })
    },
    []
  )

  const makeSelect = useCallback(
    (dim: string) => (nodeId: string) => {
      setActiveMap((prev) => ({ ...prev, [dim]: nodeId }))
      // Find node name from hierarchies for the banner
      const findName = (nodes: any[], targetId: string): string | null => {
        for (const n of nodes) {
          if (n.id === targetId) return n.name
          if (n.children) {
            const found = findName(n.children, targetId)
            if (found) return found
          }
        }
        return null
      }
      const nodeName = findName(hierarchies[dim] || [], nodeId) || nodeId
      setDimensionFilter({ dimension: dim, nodeId, nodeName })
    },
    [hierarchies, setDimensionFilter]
  )

  return (
    <aside
      className={cn(
        'flex-shrink-0 overflow-y-auto overflow-x-hidden transition-all duration-300',
        isOpen
          ? 'w-[210px] p-2.5 border-r border-border'
          : 'w-0 p-0 border-0 overflow-hidden'
      )}
      style={{ background: 'var(--surface)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-bold font-display">Dimensions</span>
      </div>

      {/* Donut progress */}
      <DonutProgress approved={12} reviewed={5} draft={8} />

      {/* BU List */}
      <BUList
        items={businessUnits}
        activeId={filters.businessUnit}
        onSelect={(buId) => setBusinessUnit(buId)}
      />

      {/* Hierarchy trees — rendered from real API data or fallbacks */}
      {Object.entries(hierarchies).map(([dim, tree]) => (
        <HierarchyTree
          key={dim}
          title={DIMENSION_LABELS[dim] || dim}
          dimension={dim}
          nodes={tree}
          expandedIds={expandedMap[dim] || new Set()}
          activeNodeId={activeMap[dim] || null}
          onToggle={makeToggle(dim)}
          onSelect={makeSelect(dim)}
          showCounts={dim === 'geography' || dim === 'segment'}
        />
      ))}
    </aside>
  )
}
