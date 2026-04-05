/**
 * Hook for the Executive Summary page.
 *
 * Fetches executive summary (headline + narrative + risks),
 * section narratives (Revenue/COGS/OpEx/Profitability),
 * and KPI summary cards from the computation service.
 */

import { useEffect, useState } from 'react';
import { useGlobalFilters } from '@/context/GlobalFiltersContext';
import { api, buildParams } from '@/utils/api';

interface SectionNarrative {
  sectionId: string;
  sectionName: string;
  narrative: string;
  keyDrivers: Array<{ accountName: string; amount: number; direction: string }>;
  narrativeConfidence: number;
}

interface ExecSummaryData {
  headline: string | null;
  fullNarrative: string | null;
  carryForwardNote: string | null;
  keyRisks: Array<{ risk: string; severity: string }>;
  crossBuThemes: Array<{ theme: string; busAffected: string[] }>;
}

interface KPICard {
  metricName: string;
  actual: number;
  comparator: number;
  varianceAmount: number;
  variancePct: number;
  isFavorable: boolean;
}

export function useExecutiveSummary() {
  const { filters } = useGlobalFilters();
  const { businessUnit } = filters;
  const [execSummary, setExecSummary] = useState<ExecSummaryData | null>(null);
  const [sections, setSections] = useState<SectionNarrative[]>([]);
  const [kpiCards, setKpiCards] = useState<KPICard[]>([]);
  const [nettingAlerts, setNettingAlerts] = useState<any[]>([]);
  const [trendAlerts, setTrendAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const period = filters.period
    ? `${filters.period.year}-${String(filters.period.month).padStart(2, '0')}`
    : '2026-05';
  const baseId = filters.comparisonBase || 'BUDGET';
  const viewId = filters.viewType || 'MTD';

  useEffect(() => {
    setLoading(true);

    const params = buildParams({ period_id: period, base_id: baseId, view_id: viewId, bu_id: businessUnit || undefined });
    const alertParams = buildParams({ period_id: period, bu_id: businessUnit || undefined });

    Promise.all([
      api.computation.get<any>(`/dashboard/executive-summary${params}`).catch(() => null),
      api.computation.get<any>(`/dashboard/section-narratives${params}`).catch(() => ({ sections: [] })),
      api.computation.get<any>(`/dashboard/summary${params}`).catch(() => ({ cards: [] })),
      api.computation.get<any>(`/dashboard/alerts/netting${alertParams}`).catch(() => ({ alerts: [] })),
      api.computation.get<any>(`/dashboard/alerts/trends${alertParams}`).catch(() => ({ alerts: [] })),
    ]).then(([exec, sectionData, summary, netting, trends]) => {
      setExecSummary(exec || null);
      setSections(sectionData?.sections || []);
      setKpiCards(summary?.cards || []);
      setNettingAlerts(netting?.alerts || []);
      setTrendAlerts(trends?.alerts || []);
    }).finally(() => setLoading(false));
  }, [period, baseId, viewId, businessUnit]);

  return { execSummary, sections, kpiCards, nettingAlerts, trendAlerts, loading };
}
