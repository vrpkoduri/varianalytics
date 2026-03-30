export enum ReviewStatus {
  AI_DRAFT = 'AI_DRAFT',
  ANALYST_REVIEWED = 'ANALYST_REVIEWED',
  APPROVED = 'APPROVED',
  ESCALATED = 'ESCALATED',
  DISMISSED = 'DISMISSED',
  AUTO_CLOSED = 'AUTO_CLOSED',
}

export enum ViewType {
  MTD = 'MTD',
  QTD = 'QTD',
  YTD = 'YTD',
}

export enum ComparisonBase {
  BUDGET = 'BUDGET',
  FORECAST = 'FORECAST',
  PRIOR_YEAR = 'PRIOR_YEAR',
}

export enum PersonaType {
  ANALYST = 'Analyst',
  BU_LEADER = 'BU Leader',
  HR_FINANCE = 'HR Finance',
  CFO = 'CFO',
  BOARD_VIEWER = 'Board Viewer',
}

export type NarrativeLevel = 'detail' | 'midlevel' | 'summary' | 'oneliner' | 'board';

export interface Period {
  year: number;
  month: number;
  label: string;
}

export interface DimensionFilter {
  dimension: string;
  nodeId: string;
  nodeName: string;
}

export interface GlobalFilters {
  period: Period | null;
  businessUnit: string | null;
  viewType: ViewType;
  comparisonBase: ComparisonBase;
  dimensionFilter: DimensionFilter | null;
}

export interface User {
  id: string;
  name: string;
  email: string;
  persona: PersonaType;
  buScope: string[];
}
