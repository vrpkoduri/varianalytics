import { cn } from '@/utils/theme'

export interface TreeNodeData {
  id: string
  name: string
  children?: TreeNodeData[]
}

export interface HierarchyTreeProps {
  title: string
  dimension: string
  nodes: TreeNodeData[]
  expandedIds: Set<string>
  activeNodeId: string | null
  onToggle: (nodeId: string) => void
  onSelect: (nodeId: string) => void
  showCounts?: boolean
  variantCounts?: Record<string, number>
}

interface TreeNodeProps {
  node: TreeNodeData
  depth: number
  expandedIds: Set<string>
  activeNodeId: string | null
  onToggle: (nodeId: string) => void
  onSelect: (nodeId: string) => void
  showCounts?: boolean
  variantCounts?: Record<string, number>
}

function TreeNode({
  node,
  depth,
  expandedIds,
  activeNodeId,
  onToggle,
  onSelect,
  showCounts,
  variantCounts,
}: TreeNodeProps) {
  const hasChildren = node.children && node.children.length > 0
  const isExpanded = expandedIds.has(node.id)
  const isActive = activeNodeId === node.id

  return (
    <>
      <div
        className={cn(
          'flex items-center gap-[3px] py-1 px-1.5 rounded-md cursor-pointer transition-all duration-150 text-[10px] font-medium',
          isActive
            ? 'bg-[rgba(0,168,199,.1)] text-teal font-semibold'
            : 'text-tx-secondary hover:bg-[rgba(0,168,199,.06)] hover:text-tx-primary'
        )}
        style={{ paddingLeft: `${6 + depth * 12}px` }}
        onClick={() => {
          if (hasChildren) onToggle(node.id)
          onSelect(node.id)
        }}
      >
        {hasChildren ? (
          <span
            className={cn(
              'w-3.5 text-center text-[8px] text-tx-tertiary flex-shrink-0 transition-transform duration-200',
              isExpanded && 'rotate-90'
            )}
            style={{ transitionTimingFunction: 'cubic-bezier(.34,1.56,.64,1)' }}
          >
            &#x203A;
          </span>
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}
        {node.name}
        {showCounts && variantCounts?.[node.id] != null && variantCounts[node.id] > 0 && (
          <span className="ml-auto text-[7px] font-bold text-teal bg-[rgba(0,168,199,.1)] rounded-md px-1">
            {variantCounts[node.id]}
          </span>
        )}
      </div>
      {hasChildren &&
        isExpanded &&
        node.children!.map((child) => (
          <TreeNode
            key={child.id}
            node={child}
            depth={depth + 1}
            expandedIds={expandedIds}
            activeNodeId={activeNodeId}
            onToggle={onToggle}
            onSelect={onSelect}
            showCounts={showCounts}
            variantCounts={variantCounts}
          />
        ))}
    </>
  )
}

export function HierarchyTree({
  title,
  nodes,
  expandedIds,
  activeNodeId,
  onToggle,
  onSelect,
  showCounts,
  variantCounts,
}: HierarchyTreeProps) {
  // Expand all top-level nodes helper
  const expandAll = () => {
    const allIds: string[] = []
    function collect(n: TreeNodeData) {
      if (n.children && n.children.length > 0) {
        allIds.push(n.id)
        n.children.forEach(collect)
      }
    }
    nodes.forEach(collect)
    allIds.forEach((id) => {
      if (!expandedIds.has(id)) onToggle(id)
    })
  }

  return (
    <div className="mt-2">
      <div className="flex items-center justify-between px-1 mb-1">
        <h6 className="text-[7px] font-bold text-teal uppercase tracking-[1.2px]">
          {title}
        </h6>
        <button
          onClick={expandAll}
          className="text-[7px] text-tx-tertiary hover:text-teal cursor-pointer font-normal normal-case tracking-normal"
        >
          expand
        </button>
      </div>
      <div className="flex flex-col">
        {nodes.map((node) => (
          <TreeNode
            key={node.id}
            node={node}
            depth={0}
            expandedIds={expandedIds}
            activeNodeId={activeNodeId}
            onToggle={onToggle}
            onSelect={onSelect}
            showCounts={showCounts}
            variantCounts={variantCounts}
          />
        ))}
      </div>
    </div>
  )
}
