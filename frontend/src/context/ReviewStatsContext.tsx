import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from 'react';

interface ReviewStats {
  pendingCount: number;
  overdueCount: number;
  approvedToday: number;
  totalInQueue: number;
}

interface ReviewStatsContextValue {
  stats: ReviewStats;
  setStats: (stats: ReviewStats) => void;
  isLoading: boolean;
}

const initialStats: ReviewStats = {
  pendingCount: 0,
  overdueCount: 0,
  approvedToday: 0,
  totalInQueue: 0,
};

const ReviewStatsContext = createContext<ReviewStatsContextValue | undefined>(
  undefined,
);

export function ReviewStatsProvider({ children }: { children: ReactNode }) {
  const [stats, setStats] = useState<ReviewStats>(initialStats);
  const [isLoading] = useState(false);

  return (
    <ReviewStatsContext.Provider value={{ stats, setStats, isLoading }}>
      {children}
    </ReviewStatsContext.Provider>
  );
}

export function useReviewStats(): ReviewStatsContextValue {
  const context = useContext(ReviewStatsContext);
  if (!context) {
    throw new Error(
      'useReviewStats must be used within a ReviewStatsProvider',
    );
  }
  return context;
}
