/**
 * Fetches available fiscal periods from the backend.
 *
 * Returns a sorted list of periods (newest first) with formatted labels.
 * Supports view-type-aware filtering:
 * - MTD: all months
 * - QTD: quarter-end months only (Mar, Jun, Sep, Dec)
 * - YTD: years only (deduplicated)
 */

import { useEffect, useState, useMemo } from 'react';
import { api } from '@/utils/api';
import type { Period } from '@/types/index';

interface PeriodOption {
  periodId: string;       // "2026-06"
  label: string;          // "Jun 2026" or "Q2 2026" or "2026"
  year: number;
  month: number;
  isClosed: boolean;
  isCurrent: boolean;
  hasData?: boolean;
}

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

const QUARTER_END_MONTHS = new Set([3, 6, 9, 12]);

function formatPeriodLabel(periodId: string, viewType?: string): string {
  const [yearStr, monthStr] = periodId.split('-');
  const month = parseInt(monthStr, 10);

  if (viewType === 'YTD') {
    return yearStr;
  }
  if (viewType === 'QTD') {
    const quarter = Math.ceil(month / 3);
    return `Q${quarter} ${yearStr}`;
  }
  return `${MONTH_NAMES[month - 1]} ${yearStr}`;
}

export function usePeriods(viewType?: string) {
  const [allPeriods, setAllPeriods] = useState<PeriodOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.gateway
      .get<any[]>('/dimensions/periods')
      .then((data) => {
        const mapped: PeriodOption[] = (data || []).map((p: any) => ({
          periodId: p.periodId || p.period_id || p.id || '',
          label: '', // Will be computed in the filtered memo
          year: p.fiscalYear || p.fiscal_year || parseInt((p.periodId || '').split('-')[0], 10),
          month: p.fiscalMonth || p.fiscal_month || parseInt((p.periodId || '').split('-')[1], 10),
          isClosed: p.isClosed ?? p.is_closed ?? true,
          isCurrent: p.isCurrent ?? p.is_current ?? false,
          hasData: p.hasData ?? p.has_data ?? false,
        }));

        // Sort newest first
        mapped.sort((a, b) => b.periodId.localeCompare(a.periodId));
        setAllPeriods(mapped);
      })
      .catch(() => {
        // Fallback: generate 36 months
        const fallback: PeriodOption[] = [];
        for (let y = 2026; y >= 2024; y--) {
          for (let m = 12; m >= 1; m--) {
            const pid = `${y}-${String(m).padStart(2, '0')}`;
            fallback.push({
              periodId: pid,
              label: '',
              year: y,
              month: m,
              isClosed: true,
              isCurrent: y === 2026 && m === 6,
              hasData: y === 2026 && m <= 6,
            });
          }
        }
        setAllPeriods(fallback);
      })
      .finally(() => setIsLoading(false));
  }, []);

  // Filter and label periods based on view type
  const periods = useMemo(() => {
    if (!allPeriods.length) return [];

    let filtered = allPeriods;

    if (viewType === 'QTD') {
      // Only quarter-end months
      filtered = allPeriods.filter(p => QUARTER_END_MONTHS.has(p.month));
    } else if (viewType === 'YTD') {
      // Deduplicate to years — use the latest month of each year
      const yearMap = new Map<number, PeriodOption>();
      for (const p of allPeriods) {
        if (!yearMap.has(p.year) || p.month > (yearMap.get(p.year)!.month)) {
          yearMap.set(p.year, p);
        }
      }
      filtered = [...yearMap.values()].sort((a, b) => b.year - a.year);
    }

    // Apply labels based on view type
    return filtered.map(p => ({
      ...p,
      label: formatPeriodLabel(p.periodId, viewType),
    }));
  }, [allPeriods, viewType]);

  const latestPeriod: Period | null = periods.length > 0
    ? { year: periods[0].year, month: periods[0].month, label: periods[0].label }
    : null;

  return { periods, latestPeriod, isLoading };
}
