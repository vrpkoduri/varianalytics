import type { ReviewStatus, NarrativeLevel } from './index';

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

export interface VarianceSummary {
  id: string;
  accountName: string;
  accountPath: string;
  actual: number;
  comparison: number;
  varianceAmount: number;
  variancePercent: number | null;
  isFavorable: boolean;
  reviewStatus: ReviewStatus;
  narrativeLevel: NarrativeLevel;
  narrative: string;
  materialityFlag: boolean;
  nettingFlag: boolean;
  trendFlag: boolean;
}

export interface DashboardData {
  totalVariances: number;
  materialVariances: number;
  favorableCount: number;
  unfavorableCount: number;
  pendingReview: number;
  approved: number;
  topVariances: VarianceSummary[];
}

export interface SSEEvent {
  type: 'token' | 'data_table' | 'mini_chart' | 'suggestion' | 'confidence' | 'netting_alert' | 'review_status' | 'done';
  payload: unknown;
}

export interface ReviewQueueItem {
  varianceId: string;
  accountName: string;
  varianceAmount: number;
  reviewStatus: ReviewStatus;
  assignedTo: string;
  createdAt: string;
  slaDeadline: string;
  isOverdue: boolean;
}

export interface DashboardSummaryCard {
  name: string;
  actual: number;
  comparator: number;
  variance: number;
  variancePct: number | null;
  isMaterial: boolean;
}

export interface WaterfallStep {
  name: string;
  value: number;
  cumulative: number;
  type: 'total' | 'positive' | 'negative';
}

export interface HeatmapRow {
  bu: string;
  cells: Array<{ category: string; variancePct: number; count: number }>;
}

export interface TrendPoint {
  period: string;
  actual: number;
  budget: number;
  forecast?: number;
}

export interface PLRow {
  accountId: string;
  accountName: string;
  parentId: string | null;
  actual: number;
  comparator: number;
  varianceAmount: number;
  variancePct: number | null;
  materialityFlag: boolean;
  isCalculated: boolean;
  isMajor?: boolean;
  isLeaf: boolean;
  depth: number;
  children?: PLRow[];
}

export interface ApprovalQueueItemApi {
  varianceId: string;
  accountName: string;
  bu: string;
  varianceAmount: number;
  variancePct: number;
  analystName: string;
  status: string;
  isEdited: boolean;
}
