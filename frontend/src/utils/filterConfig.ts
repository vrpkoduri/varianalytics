/**
 * Centralized filter relevance configuration per page.
 *
 * true = filter applies and data responds to it
 * 'scope-label' = filter is shown but section shows scope label
 * 'rbac' = filter applies via server-side RBAC (not user-selectable)
 * false = filter is hidden/not relevant for this page
 */
export type FilterRelevance = true | false | 'scope-label' | 'rbac'

export interface PageFilterConfig {
  period: FilterRelevance
  bu: FilterRelevance
  view: FilterRelevance
  base: FilterRelevance
  dimensions: FilterRelevance
  persona: FilterRelevance
}

export const PAGE_FILTER_CONFIG: Record<string, PageFilterConfig> = {
  '/':         { period: true, bu: true, view: true, base: true, dimensions: true, persona: true },
  '/executive':{ period: true, bu: true, view: true, base: true, dimensions: 'scope-label', persona: true },
  '/pl':       { period: true, bu: true, view: true, base: true, dimensions: true, persona: true },
  '/chat':     { period: true, bu: true, view: true, base: true, dimensions: true, persona: true },
  '/review':   { period: true, bu: 'rbac', view: false, base: false, dimensions: false, persona: true },
  '/approval': { period: true, bu: 'rbac', view: false, base: false, dimensions: false, persona: true },
  '/reports':  { period: false, bu: false, view: false, base: false, dimensions: false, persona: true },
  '/admin':    { period: false, bu: false, view: false, base: false, dimensions: false, persona: true },
}

/** Get the filter config for a given pathname. Defaults to dashboard config. */
export function getPageFilterConfig(pathname: string): PageFilterConfig {
  return PAGE_FILTER_CONFIG[pathname] || PAGE_FILTER_CONFIG['/']
}
