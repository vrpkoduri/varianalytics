import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  type ReactNode,
} from 'react';
import {
  ViewType,
  ComparisonBase,
  type GlobalFilters,
  type Period,
  type DimensionFilter,
} from '@/types/index';

type FilterAction =
  | { type: 'SET_PERIOD'; payload: Period | null }
  | { type: 'SET_BUSINESS_UNIT'; payload: string | null }
  | { type: 'SET_VIEW_TYPE'; payload: ViewType }
  | { type: 'SET_COMPARISON_BASE'; payload: ComparisonBase }
  | { type: 'SET_DIMENSION_FILTER'; payload: DimensionFilter | null }
  | { type: 'RESET' };

interface GlobalFiltersContextValue {
  filters: GlobalFilters;
  setPeriod: (period: Period | null) => void;
  setBusinessUnit: (bu: string | null) => void;
  setViewType: (viewType: ViewType) => void;
  setComparisonBase: (base: ComparisonBase) => void;
  setDimensionFilter: (filter: DimensionFilter | null) => void;
  resetFilters: () => void;
}

const initialFilters: GlobalFilters = {
  period: null,
  businessUnit: null,
  viewType: ViewType.MTD,
  comparisonBase: ComparisonBase.BUDGET,
  dimensionFilter: null,
};

function filtersReducer(state: GlobalFilters, action: FilterAction): GlobalFilters {
  switch (action.type) {
    case 'SET_PERIOD':
      return { ...state, period: action.payload };
    case 'SET_BUSINESS_UNIT':
      return { ...state, businessUnit: action.payload };
    case 'SET_VIEW_TYPE': {
      const newViewType = action.payload;
      let snappedPeriod = state.period;

      if (snappedPeriod && newViewType === 'QTD') {
        // Snap to floor quarter-end month: Aug→Jun, Nov→Sep, Feb→Dec(prev year)
        const quarterEndMonths = [3, 6, 9, 12];
        const currentMonth = snappedPeriod.month;
        // Find the largest quarter-end month <= current month
        const snappedMonth = quarterEndMonths.filter(m => m <= currentMonth).pop()
          || 12; // If Jan/Feb, wrap to Dec of previous year
        const snappedYear = snappedMonth === 12 && currentMonth < 3
          ? snappedPeriod.year - 1 : snappedPeriod.year;
        const quarter = Math.ceil(snappedMonth / 3);
        snappedPeriod = {
          year: snappedYear,
          month: snappedMonth,
          label: `Q${quarter} ${snappedYear}`,
        };
      }
      // YTD keeps the current period as-is (usePeriods handles display)

      return { ...state, viewType: newViewType, period: snappedPeriod };
    }
    case 'SET_COMPARISON_BASE':
      return { ...state, comparisonBase: action.payload };
    case 'SET_DIMENSION_FILTER':
      return { ...state, dimensionFilter: action.payload };
    case 'RESET':
      return initialFilters;
    default:
      return state;
  }
}

const GlobalFiltersContext = createContext<GlobalFiltersContextValue | undefined>(
  undefined,
);

export function GlobalFiltersProvider({ children }: { children: ReactNode }) {
  const [filters, dispatch] = useReducer(filtersReducer, initialFilters);

  // Initialize default period from available data on mount
  useEffect(() => {
    if (filters.period) return; // Already set
    import('@/utils/api').then(({ api }) => {
      api.gateway.get<any[]>('/dimensions/periods').then((data) => {
        if (data && data.length > 0) {
          // Sort by periodId descending, pick latest with data
          const sorted = [...data].sort((a, b) =>
            (b.periodId || b.period_id || '').localeCompare(a.periodId || a.period_id || '')
          );
          // Prefer the latest period that has actual computed data
          const withData = sorted.filter((p) => p.has_data || p.hasData);
          const latest = withData.length > 0 ? withData[0] : sorted[0];
          const pid = latest.periodId || latest.period_id || '';
          const [yearStr, monthStr] = pid.split('-');
          const MONTHS = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
          const month = parseInt(monthStr, 10);
          dispatch({
            type: 'SET_PERIOD',
            payload: {
              year: parseInt(yearStr, 10),
              month,
              label: `${MONTHS[month]} ${yearStr}`,
            },
          });
        }
      }).catch(() => {
        // Fallback: use 2026-06
        dispatch({
          type: 'SET_PERIOD',
          payload: { year: 2026, month: 6, label: 'Jun 2026' },
        });
      });
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const setPeriod = useCallback(
    (period: Period | null) => dispatch({ type: 'SET_PERIOD', payload: period }),
    [],
  );
  const setBusinessUnit = useCallback(
    (bu: string | null) => dispatch({ type: 'SET_BUSINESS_UNIT', payload: bu }),
    [],
  );
  const setViewType = useCallback(
    (viewType: ViewType) => dispatch({ type: 'SET_VIEW_TYPE', payload: viewType }),
    [],
  );
  const setComparisonBase = useCallback(
    (base: ComparisonBase) =>
      dispatch({ type: 'SET_COMPARISON_BASE', payload: base }),
    [],
  );
  const setDimensionFilter = useCallback(
    (filter: DimensionFilter | null) =>
      dispatch({ type: 'SET_DIMENSION_FILTER', payload: filter }),
    [],
  );
  const resetFilters = useCallback(() => dispatch({ type: 'RESET' }), []);

  return (
    <GlobalFiltersContext.Provider
      value={{
        filters,
        setPeriod,
        setBusinessUnit,
        setViewType,
        setComparisonBase,
        setDimensionFilter,
        resetFilters,
      }}
    >
      {children}
    </GlobalFiltersContext.Provider>
  );
}

export function useGlobalFilters(): GlobalFiltersContextValue {
  const context = useContext(GlobalFiltersContext);
  if (!context) {
    throw new Error(
      'useGlobalFilters must be used within a GlobalFiltersProvider',
    );
  }
  return context;
}
