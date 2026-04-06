/**
 * Hook for the Executive Summary page.
 *
 * Fetches executive summary (headline + narrative + risks),
 * section narratives (Revenue/COGS/OpEx/Profitability),
 * and KPI summary cards from the computation service.
 */

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';
import { useFilterParams } from '@/hooks/useFilterParams';

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
  const { query } = useFilterParams();
  const [execSummary, setExecSummary] = useState<ExecSummaryData | null>(null);
  const [sections, setSections] = useState<SectionNarrative[]>([]);
  const [kpiCards, setKpiCards] = useState<KPICard[]>([]);
  const [nettingAlerts, setNettingAlerts] = useState<any[]>([]);
  const [trendAlerts, setTrendAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);

    Promise.all([
      api.computation.get<any>(`/dashboard/executive-summary${query}`).catch(() => null),
      api.computation.get<any>(`/dashboard/section-narratives${query}`).catch(() => ({ sections: [] })),
      api.computation.get<any>(`/dashboard/summary${query}`).catch(() => ({ cards: [] })),
      api.computation.get<any>(`/dashboard/alerts/netting${query}`).catch(() => ({ alerts: [] })),
      api.computation.get<any>(`/dashboard/alerts/trends${query}`).catch(() => ({ alerts: [] })),
    ]).then(([exec, sectionData, summary, netting, trends]) => {
      setExecSummary(exec || null);
      setSections(sectionData?.sections || []);
      setKpiCards(summary?.cards || []);
      setNettingAlerts(netting?.alerts || []);
      setTrendAlerts(trends?.alerts || []);
    }).finally(() => setLoading(false));
  }, [query]);

  return { execSummary, sections, kpiCards, nettingAlerts, trendAlerts, loading };
}
