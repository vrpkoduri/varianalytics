/**
 * Fetches available fiscal periods from the backend.
 *
 * Returns a sorted list of periods (newest first) with formatted labels,
 * plus the latest period for default selection.
 */

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';
import type { Period } from '@/types/index';

interface PeriodOption {
  periodId: string;       // "2026-06"
  label: string;          // "Jun 2026"
  year: number;
  month: number;
  isClosed: boolean;
  isCurrent: boolean;
}

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

function formatPeriodLabel(periodId: string): string {
  const [yearStr, monthStr] = periodId.split('-');
  const month = parseInt(monthStr, 10);
  return `${MONTH_NAMES[month - 1]} ${yearStr}`;
}

export function usePeriods() {
  const [periods, setPeriods] = useState<PeriodOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.gateway
      .get<any[]>('/dimensions/periods')
      .then((data) => {
        const mapped: PeriodOption[] = (data || []).map((p: any) => ({
          periodId: p.periodId || p.period_id || p.id || '',
          label: formatPeriodLabel(p.periodId || p.period_id || p.id || ''),
          year: p.fiscalYear || p.fiscal_year || parseInt((p.periodId || '').split('-')[0], 10),
          month: p.fiscalMonth || p.fiscal_month || parseInt((p.periodId || '').split('-')[1], 10),
          isClosed: p.isClosed ?? p.is_closed ?? true,
          isCurrent: p.isCurrent ?? p.is_current ?? false,
        }));

        // Sort newest first
        mapped.sort((a, b) => b.periodId.localeCompare(a.periodId));
        setPeriods(mapped);
      })
      .catch(() => {
        // Fallback: generate 12 months ending at 2026-06
        const fallback: PeriodOption[] = [];
        for (let i = 0; i < 12; i++) {
          const m = 6 - i;
          const y = m > 0 ? 2026 : 2025;
          const month = m > 0 ? m : m + 12;
          const pid = `${y}-${String(month).padStart(2, '0')}`;
          fallback.push({
            periodId: pid,
            label: formatPeriodLabel(pid),
            year: y,
            month,
            isClosed: true,
            isCurrent: i === 0,
          });
        }
        setPeriods(fallback);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const latestPeriod: Period | null = periods.length > 0
    ? { year: periods[0].year, month: periods[0].month, label: periods[0].label }
    : null;

  return { periods, latestPeriod, isLoading };
}
