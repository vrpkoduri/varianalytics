import type { ReviewStatus, NarrativeLevel, ViewType, ComparisonBase } from './index';

export interface DimHierarchy {
  nodeId: string;
  parentId: string | null;
  name: string;
  level: number;
  rollupPath: string;
  dimensionType: 'Geo' | 'Segment' | 'LOB' | 'CostCenter';
}

export interface DimBusinessUnit {
  buId: string;
  name: string;
  code: string;
}

export interface DimAccount {
  accountId: string;
  parentId: string | null;
  name: string;
  level: number;
  isCalculated: boolean;
  rollupPath: string;
  signConvention: 'natural' | 'reversed';
}

export interface DimPeriod {
  periodId: string;
  year: number;
  month: number;
  quarter: number;
  label: string;
  isClosed: boolean;
}

export interface FactFinancials {
  id: string;
  periodId: string;
  accountId: string;
  buId: string;
  actual: number;
  budget: number;
  forecast: number;
  priorYear: number;
  fxActual: number | null;
  fxBudget: number | null;
}

export interface FactVarianceMaterial {
  id: string;
  periodId: string;
  accountId: string;
  buId: string;
  viewType: ViewType;
  comparisonBase: ComparisonBase;
  varianceAmount: number;
  variancePercent: number | null;
  isFavorable: boolean;
  materialityFlag: boolean;
  nettingFlag: boolean;
  trendFlag: boolean;
  narratives: Record<NarrativeLevel, string>;
  synthesisStatus: 'pending' | 'complete';
}

export interface FactDecomposition {
  id: string;
  varianceId: string;
  component: string;
  amount: number;
  percent: number | null;
  method: string;
}

export interface FactReviewStatus {
  id: string;
  varianceId: string;
  status: ReviewStatus;
  analystId: string | null;
  reviewedAt: string | null;
  approvedBy: string | null;
  approvedAt: string | null;
  editedNarrative: string | null;
  hypothesisFeedback: 'up' | 'down' | null;
}

export interface KnowledgeCommentary {
  id: string;
  varianceId: string;
  accountId: string;
  narrative: string;
  narrativeLevel: NarrativeLevel;
  approvedAt: string;
  embedding: number[] | null;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: string;
  userId: string;
  detail: string;
}
