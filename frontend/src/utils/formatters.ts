/**
 * Format a number as currency (USD).
 */
export function formatCurrency(value: number, decimals = 0): string {
  const absValue = Math.abs(value);
  if (absValue >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (absValue >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (absValue >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}K`;
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format a number as a full currency value without abbreviation.
 */
export function formatCurrencyFull(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format a number as percentage.
 * Returns null display string for null input (e.g. budget=0 cases).
 */
export function formatPercent(value: number | null, decimals = 1): string {
  if (value === null) return 'N/A';
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

/**
 * Format a variance amount with sign and color hint.
 */
export function formatVariance(amount: number, isFavorable: boolean): string {
  const formatted = formatCurrency(Math.abs(amount));
  const sign = amount >= 0 ? '+' : '-';
  const direction = isFavorable ? 'F' : 'U';
  return `${sign}${formatted} ${direction}`;
}

/**
 * Format a date string to a human-readable format.
 */
export function formatDate(dateStr: string, style: 'short' | 'long' = 'short'): string {
  const date = new Date(dateStr);
  if (style === 'long') {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a period label from year and month.
 */
export function formatPeriodLabel(year: number, month: number): string {
  const date = new Date(year, month - 1);
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
}
