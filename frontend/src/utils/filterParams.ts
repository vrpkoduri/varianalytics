/**
 * Unified filter parameter utilities.
 *
 * Centralizes the construction of API query parameters from the
 * global filter state. Every data-fetching hook uses this instead
 * of manually building params — guaranteeing consistent filter
 * propagation across all sections and pages.
 */

export interface FilterParams {
  period_id: string
  view_id: string
  base_id: string
  bu_id?: string
  geo_node_id?: string
  segment_node_id?: string
  lob_node_id?: string
  costcenter_node_id?: string
  persona?: string
}

/**
 * Build a URL query string from FilterParams.
 *
 * Omits undefined/null values. Returns a string starting with "?"
 * or empty string if no params.
 *
 * @example
 * buildFilterQuery({ period_id: '2026-06', view_id: 'MTD', base_id: 'BUDGET', bu_id: 'marsh' })
 * // => "?period_id=2026-06&view_id=MTD&base_id=BUDGET&bu_id=marsh"
 */
export function buildFilterQuery(params: FilterParams, extras?: Record<string, string | number | undefined>): string {
  const entries: [string, string][] = []

  // Core params (always present)
  entries.push(['period_id', params.period_id])
  entries.push(['view_id', params.view_id])
  entries.push(['base_id', params.base_id])

  // Optional params
  if (params.bu_id) entries.push(['bu_id', params.bu_id])
  if (params.geo_node_id) entries.push(['geo_node_id', params.geo_node_id])
  if (params.segment_node_id) entries.push(['segment_node_id', params.segment_node_id])
  if (params.lob_node_id) entries.push(['lob_node_id', params.lob_node_id])
  if (params.costcenter_node_id) entries.push(['costcenter_node_id', params.costcenter_node_id])
  if (params.persona) entries.push(['persona', params.persona])

  // Extra params (page-specific)
  if (extras) {
    for (const [key, val] of Object.entries(extras)) {
      if (val !== undefined && val !== null) {
        entries.push([key, String(val)])
      }
    }
  }

  if (entries.length === 0) return ''
  const qs = entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&')
  return `?${qs}`
}
