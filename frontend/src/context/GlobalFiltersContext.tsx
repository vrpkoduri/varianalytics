import {
  createContext,
  useCallback,
  useContext,
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
    case 'SET_VIEW_TYPE':
      return { ...state, viewType: action.payload };
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
