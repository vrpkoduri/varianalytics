/**
 * Account name display formatting utility.
 *
 * Converts raw account IDs (e.g. "acct_pbt", "acct_revenue_product")
 * to human-readable display names. Acts as a frontend safety net for
 * cases where backend account_name lookup is unavailable.
 */

/** Canonical account display names keyed by account_id. */
export const ACCOUNT_DISPLAY_NAMES: Record<string, string> = {
  // P&L top-level
  acct_revenue: 'Revenue',
  acct_revenue_product: 'Product Revenue',
  acct_revenue_service: 'Service Revenue',
  acct_revenue_licensing: 'Licensing Revenue',
  acct_revenue_subscription: 'Subscription Revenue',
  acct_revenue_other: 'Other Revenue',
  // COGS
  acct_cogs: 'Cost of Goods Sold',
  acct_cogs_materials: 'Materials',
  acct_cogs_labor: 'Direct Labor',
  acct_cogs_overhead: 'Manufacturing Overhead',
  acct_cogs_freight: 'Freight & Logistics',
  // Gross Profit (calculated)
  acct_gross_profit: 'Gross Profit',
  // OpEx
  acct_opex: 'Operating Expenses',
  acct_opex_salaries: 'Salaries & Wages',
  acct_opex_benefits: 'Employee Benefits',
  acct_opex_contractors: 'Contractor Costs',
  acct_opex_training: 'Training & Development',
  acct_opex_recruitment: 'Recruitment',
  acct_opex_rent: 'Rent & Facilities',
  acct_opex_utilities: 'Utilities',
  acct_opex_travel: 'Travel & Entertainment',
  acct_opex_marketing: 'Marketing & Advertising',
  acct_opex_software: 'Software & Licenses',
  acct_opex_depreciation: 'Depreciation',
  acct_opex_insurance: 'Insurance',
  acct_opex_professional: 'Professional Services',
  acct_opex_other: 'Other Operating Expenses',
  // Calculated rows
  acct_ebitda: 'EBITDA',
  acct_ebit: 'EBIT',
  acct_pbt: 'Pre-Tax Income',
  acct_net_income: 'Net Income',
  acct_operating_income: 'Operating Income',
  // Interest / Tax
  acct_interest: 'Interest Expense',
  acct_tax: 'Income Tax',
  // Headcount
  acct_headcount: 'Headcount',
}

/**
 * Format a raw account ID into a human-readable display name.
 *
 * Looks up the canonical name first; falls back to a cleaned-up
 * title-case version of the ID.
 *
 * @param id - Raw account ID (e.g. "acct_pbt", "acct_revenue_product")
 * @returns Display name (e.g. "Pre-Tax Income", "Product Revenue")
 */
export function formatAccountName(id: string): string {
  // Check canonical map first
  const canonical = ACCOUNT_DISPLAY_NAMES[id]
  if (canonical) return canonical

  // Fallback: strip prefix and title-case
  return id
    .replace(/^acct_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}
