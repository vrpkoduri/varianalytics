/**
 * Data transformers — map backend API responses to frontend component shapes.
 *
 * After snakeToCamel conversion in api.ts, API fields use camelCase but may
 * still have different names, types, or structures than what components expect.
 *
 * Each function takes the raw API response (post-snakeToCamel) and returns
 * the exact shape the component expects (matching mock data interfaces).
 */

import type { MockKPICard, WaterfallStep, TrendPoint, HeatmapData } from '@/mocks/dashboardData'
import type { MockVariance } from '@/mocks/dashboardData'
import type { PLRowData } from '@/mocks/plData'
import type { ReviewVariance } from '@/mocks/reviewData'
import type { ApprovalVariance } from '@/mocks/approvalData'

// ============================================================
// Shared helpers
// ============================================================

function round2(val: number): number {
  return Math.round(val * 100) / 100
}

function formatK(val: number): string {
  return `${Math.round(val / 1000).toLocaleString()}K`
}

function formatLabel(name: string): string {
  return name
    .replace(/^Total\s+/i, '')
    .replace(/^Gross\s+/i, '')
    .toUpperCase()
}

function formatBU(id: string): string {
  const map: Record<string, string> = {
    marsh: 'Marsh',
    mercer: 'Mercer',
    guy_carpenter: 'Guy Carpenter',
    oliver_wyman: 'Oliver Wyman',
    mmc_corporate: 'MMC Corporate',
  }
  return map[id] || id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatGeo(id: string): string {
  const map: Record<string, string> = {
    geo_us_ne: 'US NE',
    geo_us_se: 'US SE',
    geo_us_mw: 'US MW',
    geo_us_w: 'US W',
    geo_uk_ireland: 'UK',
    geo_france: 'France',
    geo_germany: 'Germany',
    geo_india: 'India',
    geo_japan: 'Japan',
    geo_singapore: 'Singapore',
    geo_anz: 'ANZ',
    geo_hong_kong: 'Hong Kong',
    geo_netherlands: 'Netherlands',
    geo_canada: 'Canada',
  }
  return map[id] || id.replace(/^geo_/, '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function mapStatus(s: string): 'approved' | 'reviewed' | 'draft' {
  const map: Record<string, 'approved' | 'reviewed' | 'draft'> = {
    AI_DRAFT: 'draft',
    ANALYST_REVIEWED: 'reviewed',
    APPROVED: 'approved',
    ESCALATED: 'draft',
    DISMISSED: 'draft',
    AUTO_CLOSED: 'draft',
    // Post-camelCase versions
    aiDraft: 'draft',
    analystReviewed: 'reviewed',
    approved: 'approved',
    reviewed: 'reviewed',
    draft: 'draft',
  }
  return map[s] || 'draft'
}

// ============================================================
// KPI Summary Cards
// ============================================================
// API (post-camelCase): { metricName, accountId, actual, comparator, varianceAmount, variancePct, isFavorable, isMaterial }
// Component (MockKPICard): { id, label, value, prefix, suffix, delta, favorable, comparator, comparatorLabel, sparkData }

export function transformSummaryCards(apiCards: any[]): MockKPICard[] {
  if (!Array.isArray(apiCards)) return []
  return apiCards.map((c) => ({
    id: c.accountId || c.metricName || 'unknown',
    label: formatLabel(c.metricName || ''),
    value: Math.round((c.actual || 0) / 1000),
    prefix: '$',
    suffix: 'K',
    delta: round2(c.variancePct ?? 0),
    favorable: c.isFavorable ?? ((c.varianceAmount ?? 0) > 0),
    comparator: Math.round((c.comparator || 0) / 1000),
    comparatorLabel: `vs $${formatK(c.comparator || 0)}`,
    sparkData: c.sparkData || [],
  }))
}

// ============================================================
// Waterfall Chart Steps
// ============================================================
// API (post-camelCase): { name, value, cumulative, isTotal, isPositive }
// Component (WaterfallStep): { name, value, cumulative, type: 'total'|'positive'|'negative' }

export function transformWaterfallSteps(apiSteps: any[]): WaterfallStep[] {
  if (!Array.isArray(apiSteps)) return []
  return apiSteps.map((s) => ({
    name: s.name || '',
    value: round2((s.value || 0) / 1000),
    cumulative: round2((s.cumulative || 0) / 1000),
    type: s.isTotal
      ? ('total' as const)
      : (s.isPositive ?? (s.value >= 0))
        ? ('positive' as const)
        : ('negative' as const),
  }))
}

// ============================================================
// Trend Chart Data
// ============================================================
// API (post-camelCase): { periodId, actual, comparator, varianceAmount, variancePct }
// Component (TrendPoint): { month: string, actual: number, budget: number }

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

export function transformTrendData(apiData: any[]): TrendPoint[] {
  if (!Array.isArray(apiData)) return []
  return apiData.map((d) => {
    const periodId = d.periodId || ''
    const monthIdx = parseInt(periodId.split('-')[1] || '0', 10) - 1
    return {
      month: MONTH_NAMES[monthIdx] ?? periodId,
      actual: Math.round((d.actual || 0) / 1000),
      budget: Math.round((d.comparator || d.budget || 0) / 1000),
    }
  })
}

// ============================================================
// Heatmap
// ============================================================
// API (post-camelCase): { rows: string[] (geos), columns: string[] (BUs), cells: { value, pct, isMaterial }[][] }
// Component (HeatmapData): { columns: string[], rows: { bu: string, cells: number[] }[] }
// Backend has geos as rows, BUs as columns — component expects BUs as rows

export function transformHeatmap(api: any): HeatmapData | null {
  if (!api || !api.rows || !api.columns || !api.cells) return null

  const geoNames: string[] = api.rows
  const buNames: string[] = api.columns

  // Limit to 5 columns (geos) for UI fit
  const displayGeos = geoNames.slice(0, 5)

  return {
    columns: displayGeos.map((g: string) =>
      g.replace(/^geo_/, '').replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
    ),
    rows: buNames.map((bu: string, buIdx: number) => ({
      bu: bu.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
      cells: displayGeos.map((_: string, geoIdx: number) => {
        const cell = api.cells?.[geoIdx]?.[buIdx]
        return round2(cell?.pct ?? cell?.variancePct ?? 0)
      }),
    })),
  }
}

// ============================================================
// Variance Table Items
// ============================================================
// API (post-camelCase): { varianceId, accountId, accountName, buId, geoNodeId, actualAmount, comparatorAmount,
//   varianceAmount, variancePct, isMaterial, isNetted, isTrending, plCategory, narrativeOneliner }
// Component (MockVariance): { id, account, bu, geo, variance, variancePct, favorable, sparkData, type, status, edgeBadge, narrative }

export function transformVariances(apiItems: any[]): MockVariance[] {
  if (!Array.isArray(apiItems)) return []
  return apiItems.map((v) => ({
    id: v.varianceId || v.id || '',
    account: v.accountName || v.account || '',
    bu: formatBU(v.buId || v.bu || ''),
    geo: formatGeo(v.geoNodeId || v.geo || ''),
    variance: round2(v.varianceAmount || v.variance || 0),
    variancePct: round2(v.variancePct || 0),
    favorable: (() => {
      if (v.isFavorable !== undefined && v.isFavorable !== null) return v.isFavorable
      const amount = v.varianceAmount || v.variance || 0
      const sign = v.varianceSign || v.variance_sign || ''
      // Inverse sign convention: costs are favorable when negative
      if (sign === 'inverse' || ['COGS', 'OpEx', 'NonOp', 'Tax'].includes(v.plCategory || '')) {
        return amount < 0
      }
      return amount > 0
    })(),
    sparkData: v.sparkData || [],
    type: v.isMaterial ? 'material' : v.isNetted ? 'netted' : v.isTrending ? 'trending' : 'material',
    status: mapStatus(v.status || v.reviewStatus || 'draft'),
    edgeBadge: v.edgeBadge || (v.isNew ? 'New' : undefined),
    narrative: v.narrativeOneliner || v.narrative || '',
    narrativeDetail: v.narrativeDetail || '',
    narrativeSource: v.narrativeSource || '',
  }))
}

// ============================================================
// P&L Statement Rows (flatten nested tree -> flat array)
// ============================================================
// API (post-camelCase): nested tree with { accountId, accountName, depth, isCalculated, isLeaf,
//   actual, comparator, varianceAmount, variancePct, isMaterial, plCategory, children: [...] }
// Component (PLRowData): flat array { id, name, depth, isContainer, children, isLeaf, parentId,
//   isCalculated, isMajor, actual, budget, signConvention, status, type, varianceId }

const MAJOR_CALC_NAMES = ['gross profit', 'ebitda', 'operating income', 'op income', 'pre-tax income', 'net income']
const INVERSE_CATEGORIES = ['cogs', 'opex', 'nonop', 'tax', 'cor', 'cost of revenue', 'operating expenses']

export function transformPLRows(apiTree: any[]): PLRowData[] {
  if (!Array.isArray(apiTree)) return []
  const result: PLRowData[] = []

  function flatten(nodes: any[], parentId: string | null = null) {
    for (const node of nodes) {
      const children = node.children || []
      const hasChildren = children.length > 0
      const name = node.accountName || ''
      const plCat = (node.plCategory || '').toLowerCase()

      result.push({
        id: node.accountId || '',
        name,
        depth: node.depth ?? 0,
        isContainer: hasChildren && !node.isCalculated,
        children: hasChildren ? children.map((c: any) => c.accountId) : undefined,
        isLeaf: node.isLeaf ?? !hasChildren,
        parentId: parentId ?? undefined,
        isCalculated: node.isCalculated || false,
        isMajor: MAJOR_CALC_NAMES.some((n) => name.toLowerCase().includes(n)),
        actual: Math.round(((node.actual ?? node.actualAmount ?? 0)) / 1000),
        budget: Math.round(((node.comparator ?? node.comparatorAmount ?? 0)) / 1000),
        signConvention: INVERSE_CATEGORIES.some((cat) => plCat.includes(cat)) ? 'inverse' : 'normal',
        status: node.status ? mapStatus(node.status) : undefined,
        type: node.isMaterial ? 'material' : node.isTrending ? 'trending' : undefined,
      })

      if (hasChildren) {
        flatten(children, node.accountId)
      }
    }
  }

  flatten(apiTree)
  return result
}

// ============================================================
// Review Queue Items
// ============================================================
// API (post-camelCase): similar to variances but with review-specific fields
// Component (ReviewVariance): { id, account, bu, geo, variance, variancePct, favorable, type,
//   status, sla, sparkData, edgeBadge, isEdited, isSynthesized, narratives, decomposition, hypotheses }

export function transformReviewItems(apiItems: any[]): ReviewVariance[] {
  if (!Array.isArray(apiItems)) return []
  return apiItems.map((v) => ({
    id: v.varianceId || v.id || '',
    account: v.accountName || v.account || '',
    bu: formatBU(v.buId || v.bu || ''),
    geo: formatGeo(v.geoNodeId || v.geo || ''),
    variance: round2(v.varianceAmount || v.variance || 0),
    variancePct: round2(v.variancePct || 0),
    favorable: v.isFavorable ?? ((v.varianceAmount || 0) > 0),
    type: (v.isTrending ? 'trending' : v.isNetted ? 'netted' : 'material') as ReviewVariance['type'],
    status: mapStatus(v.currentStatus || v.status || 'draft'),
    sla: v.slaHoursRemaining || v.sla || 0,
    sparkData: v.sparkData || [],
    edgeBadge: v.edgeBadge,
    isEdited: v.isEdited || false,
    editedBy: v.editedBy,
    isSynthesized: v.isSynthesized || false,
    synthCount: v.synthCount,
    narratives: v.narratives || {
      detail: v.narrativePreview || v.narrativeOneliner || '',
      midlevel: '',
      summary: '',
      board: '',
    },
    decomposition: v.decomposition || [],
    hypotheses: v.hypotheses || [],
    varianceId: v.varianceId,
  }))
}

// ============================================================
// Approval Queue Items
// ============================================================
// API (post-camelCase): similar to review items but with assignedAnalyst
// Component (ApprovalVariance): { id, account, bu, geo, variance, variancePct, favorable, status, assignedAnalyst, isEdited }

export function transformApprovalItems(apiItems: any[]): ApprovalVariance[] {
  if (!Array.isArray(apiItems)) return []
  return apiItems.map((v) => ({
    id: v.varianceId || v.id || '',
    account: v.accountName || v.account || '',
    bu: formatBU(v.buId || v.bu || ''),
    geo: formatGeo(v.geoNodeId || v.geo || ''),
    variance: round2(v.varianceAmount || v.variance || 0),
    variancePct: round2(v.variancePct || 0),
    favorable: v.isFavorable ?? ((v.varianceAmount || 0) > 0),
    status: (v.currentStatus === 'APPROVED' || v.status === 'approved' ? 'approved' : 'reviewed') as ApprovalVariance['status'],
    assignedAnalyst: v.assignedAnalyst || v.analystName || 'Unassigned',
    isEdited: v.isEdited || false,
    varianceId: v.varianceId,
  }))
}

// ============================================================
// Business Units (for sidebar BU list)
// ============================================================
export function transformBusinessUnits(apiData: any): Array<{ id: string | null; name: string; varianceCount?: number }> {
  if (!apiData) return []
  const items = Array.isArray(apiData) ? apiData : apiData.items || apiData.businessUnits || []
  const bus = items.map((bu: any) => ({
    id: bu.buId || bu.bu_id || bu.id || '',
    name: bu.buName || bu.bu_name || bu.name || '',
  }))
  return [{ id: null, name: 'All' }, ...bus]
}

// ============================================================
// Hierarchy Trees (for sidebar dimension trees)
// ============================================================
export interface TreeNodeData {
  id: string
  name: string
  children?: TreeNodeData[]
  variantCount?: number
}

export function transformHierarchyTree(apiData: any): TreeNodeData[] {
  if (!apiData) return []

  // API returns { dimensionName, roots: [...] } after snakeToCamel
  const items = Array.isArray(apiData)
    ? apiData
    : apiData.roots || apiData.nodes || apiData.items || apiData.hierarchy || []

  if (items.length === 0) return []

  // Check if it's already a tree (has children property)
  if (items[0]?.children) {
    return items.map(transformTreeNode)
  }

  // Build tree from flat list with parentId
  return buildTreeFromFlat(items)
}

function transformTreeNode(node: any): TreeNodeData {
  return {
    id: node.nodeId || node.node_id || node.id || '',
    name: node.nodeName || node.node_name || node.name || '',
    children: (node.children || []).map(transformTreeNode),
    variantCount: node.variantCount || node.variant_count,
  }
}

// ============================================================
// Decomposition Components (for modal)
// ============================================================
// API returns either an array of {componentName, amount, pctOfTotal}
// or a dict like {volume: -160.95, price: -67.06, mix: ...}

export function transformDecompositionComponents(
  components: any
): Array<{ label: string; value: number; pct: number }> {
  if (!components) return []

  if (Array.isArray(components)) {
    return components.map((c: any) => ({
      label: (c.componentName || c.component_name || c.label || 'Unknown').replace(/_/g, ' '),
      value: round2(c.amount || c.value || 0),
      pct: round2(c.pctOfTotal || c.pct_of_total || c.pct || 0),
    }))
  }

  // Dict format: { volume: -160.95, price: -67.06, ... }
  if (typeof components === 'object') {
    const total = Object.values(components).reduce((sum: number, v: any) => sum + Math.abs(Number(v) || 0), 0)
    return Object.entries(components)
      .filter(([k]) => k !== 'residual' && k !== 'method' && k !== 'is_fallback' && k !== 'isFallback')
      .map(([key, val]) => ({
        label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        value: round2(Number(val) || 0),
        pct: total > 0 ? round2((Math.abs(Number(val) || 0) / total) * 100) : 0,
      }))
  }

  return []
}

function buildTreeFromFlat(items: any[]): TreeNodeData[] {
  const nodeMap = new Map<string, TreeNodeData>()
  const roots: TreeNodeData[] = []

  // Create all nodes
  for (const item of items) {
    const id = item.nodeId || item.node_id || item.id || ''
    nodeMap.set(id, {
      id,
      name: item.nodeName || item.node_name || item.name || '',
      children: [],
    })
  }

  // Build parent-child relationships
  for (const item of items) {
    const id = item.nodeId || item.node_id || item.id || ''
    const parentId = item.parentId || item.parent_id || item.parentNodeId
    const node = nodeMap.get(id)!

    if (parentId && nodeMap.has(parentId)) {
      nodeMap.get(parentId)!.children!.push(node)
    } else {
      roots.push(node)
    }
  }

  return roots
}
