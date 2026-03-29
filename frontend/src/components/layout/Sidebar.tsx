import { useState, useCallback } from 'react'
import { DonutProgress } from '../sidebar/DonutProgress'
import { BUList } from '../sidebar/BUList'
import { HierarchyTree, type TreeNodeData } from '../sidebar/HierarchyTree'
import { cn } from '@/utils/theme'

// ── Mock hierarchy data ──────────────────────────────────────────────

const MOCK_GEO: TreeNodeData[] = [
  {
    id: 'global',
    name: 'Global',
    children: [
      {
        id: 'americas',
        name: 'Americas',
        children: [
          {
            id: 'us',
            name: 'United States',
            children: [
              { id: 'us_ne', name: 'US Northeast' },
              { id: 'us_se', name: 'US Southeast' },
              { id: 'us_mw', name: 'US Midwest' },
              { id: 'us_w', name: 'US West' },
            ],
          },
          { id: 'canada', name: 'Canada' },
          { id: 'latam', name: 'Latin America' },
        ],
      },
      {
        id: 'emea',
        name: 'EMEA',
        children: [
          { id: 'uk_ireland', name: 'UK & Ireland' },
          { id: 'europe', name: 'Continental Europe' },
          { id: 'mena', name: 'Middle East & Africa' },
        ],
      },
      {
        id: 'apac',
        name: 'Asia Pacific',
        children: [
          { id: 'anz', name: 'Australia & NZ' },
          { id: 'japan', name: 'Japan' },
          { id: 'india', name: 'India' },
          { id: 'singapore', name: 'Singapore' },
        ],
      },
    ],
  },
]

const MOCK_SEGMENT: TreeNodeData[] = [
  {
    id: 'all_seg',
    name: 'All Segments',
    children: [
      { id: 'commercial', name: 'Commercial' },
      { id: 'consumer', name: 'Consumer' },
      { id: 'specialty', name: 'Specialty' },
      { id: 'government', name: 'Government' },
    ],
  },
]

const MOCK_LOB: TreeNodeData[] = [
  {
    id: 'all_lob',
    name: 'All LOBs',
    children: [
      { id: 'risk_advisory', name: 'Risk Advisory' },
      { id: 'consulting', name: 'Consulting' },
      { id: 'reinsurance', name: 'Reinsurance' },
      { id: 'wealth', name: 'Wealth' },
      { id: 'dna', name: 'D&A' },
    ],
  },
]

const MOCK_CC: TreeNodeData[] = [
  {
    id: 'all_cc',
    name: 'All Cost Centers',
    children: [
      { id: 'client_ops', name: 'Client Operations' },
      { id: 'corporate', name: 'Corporate' },
      { id: 'technology', name: 'Technology' },
      { id: 'executive', name: 'Executive' },
    ],
  },
]

const MOCK_VARIANT_COUNTS: Record<string, number> = {
  marsh: 8,
  mercer: 5,
  guy_carpenter: 3,
  oliver_wyman: 4,
  mmc_corporate: 2,
  us: 6,
  emea: 4,
  apac: 3,
  commercial: 5,
  specialty: 3,
}

// ── Component ────────────────────────────────────────────────────────

interface SidebarProps {
  isOpen: boolean
}

export default function Sidebar({ isOpen }: SidebarProps) {
  const [activeBU, setActiveBU] = useState<string | null>(null)

  // Tree state per dimension
  const [geoExpanded, setGeoExpanded] = useState<Set<string>>(new Set(['global']))
  const [segExpanded, setSegExpanded] = useState<Set<string>>(new Set(['all_seg']))
  const [lobExpanded, setLobExpanded] = useState<Set<string>>(new Set(['all_lob']))
  const [ccExpanded, setCcExpanded] = useState<Set<string>>(new Set(['all_cc']))

  const [activeGeo, setActiveGeo] = useState<string | null>(null)
  const [activeSeg, setActiveSeg] = useState<string | null>(null)
  const [activeLob, setActiveLob] = useState<string | null>(null)
  const [activeCc, setActiveCc] = useState<string | null>(null)

  const makeToggle = useCallback(
    (setter: React.Dispatch<React.SetStateAction<Set<string>>>) => (id: string) => {
      setter((prev) => {
        const next = new Set(prev)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        return next
      })
    },
    []
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
      <BUList activeBU={activeBU} onBUSelect={setActiveBU} variantCounts={MOCK_VARIANT_COUNTS} />

      {/* Hierarchy trees */}
      <HierarchyTree
        title="Geography"
        dimension="geo"
        nodes={MOCK_GEO}
        expandedIds={geoExpanded}
        activeNodeId={activeGeo}
        onToggle={makeToggle(setGeoExpanded)}
        onSelect={setActiveGeo}
        showCounts
        variantCounts={MOCK_VARIANT_COUNTS}
      />

      <HierarchyTree
        title="Segment"
        dimension="segment"
        nodes={MOCK_SEGMENT}
        expandedIds={segExpanded}
        activeNodeId={activeSeg}
        onToggle={makeToggle(setSegExpanded)}
        onSelect={setActiveSeg}
        showCounts
        variantCounts={MOCK_VARIANT_COUNTS}
      />

      <HierarchyTree
        title="Line of Business"
        dimension="lob"
        nodes={MOCK_LOB}
        expandedIds={lobExpanded}
        activeNodeId={activeLob}
        onToggle={makeToggle(setLobExpanded)}
        onSelect={setActiveLob}
      />

      <HierarchyTree
        title="Cost Center"
        dimension="costcenter"
        nodes={MOCK_CC}
        expandedIds={ccExpanded}
        activeNodeId={activeCc}
        onToggle={makeToggle(setCcExpanded)}
        onSelect={setActiveCc}
      />
    </aside>
  )
}
