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
