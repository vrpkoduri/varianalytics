/**
 * Sidebar — route-aware dimension tree tests.
 *
 * Verifies that the sidebar conditionally renders dimension
 * hierarchy trees based on the current pathname prop.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import Sidebar from '../layout/Sidebar'

// ---- Mocks ----

// Mock useDimensions to provide stable hierarchy data
vi.mock('@/hooks/useDimensions', () => ({
  useDimensions: () => ({
    businessUnits: [
      { id: null, name: 'All' },
      { id: 'marsh', name: 'Marsh' },
    ],
    hierarchies: {
      geography: [{ id: 'global', name: 'Global', children: [] }],
      segment: [{ id: 'all_seg', name: 'All Segments', children: [] }],
      lob: [{ id: 'all_lob', name: 'All LOB', children: [] }],
      costcenter: [{ id: 'all_cc', name: 'All Cost Centers', children: [] }],
    },
    loading: false,
  }),
}))

// Mock useGlobalFilters
vi.mock('@/context/GlobalFiltersContext', () => ({
  useGlobalFilters: () => ({
    filters: {
      businessUnit: null,
      viewType: 'MTD',
      comparisonBase: 'BUDGET',
      period: null,
      dimensionFilter: null,
    },
    setBusinessUnit: vi.fn(),
    setDimensionFilter: vi.fn(),
  }),
}))

// Mock useVariances
vi.mock('@/hooks/useVariances', () => ({
  useVariances: () => ({
    variances: [],
    total: 0,
    loading: false,
  }),
}))

// Mock sidebar sub-components to simplify rendering
vi.mock('../sidebar/DonutProgress', () => ({
  DonutProgress: () => <div data-testid="donut-progress" />,
}))

vi.mock('../sidebar/BUList', () => ({
  BUList: () => <div data-testid="bu-list" />,
}))

vi.mock('../sidebar/HierarchyTree', () => ({
  HierarchyTree: ({ title }: { title: string }) => (
    <div data-testid={`tree-${title}`}>{title}</div>
  ),
}))

// Mock MOCK_VARIANCES to avoid import issues
vi.mock('@/mocks/dashboardData', () => ({
  MOCK_VARIANCES: [],
}))

// Mock theme utility
vi.mock('@/utils/theme', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}))

// ---- Tests ----

describe('Sidebar route-aware dimension trees', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows dimension trees on dashboard (pathname="/")', () => {
    render(<Sidebar isOpen={true} pathname="/" />)

    expect(screen.getByText('Geography')).toBeTruthy()
    expect(screen.getByText('Segment')).toBeTruthy()
    expect(screen.getByText('Line of Business')).toBeTruthy()
    expect(screen.getByText('Cost Center')).toBeTruthy()
  })

  it('shows dimension trees on P&L page (pathname="/pl")', () => {
    render(<Sidebar isOpen={true} pathname="/pl" />)

    expect(screen.getByText('Geography')).toBeTruthy()
    expect(screen.getByText('Segment')).toBeTruthy()
    expect(screen.getByText('Line of Business')).toBeTruthy()
    expect(screen.getByText('Cost Center')).toBeTruthy()
  })

  it('hides dimension trees on review page (pathname="/review")', () => {
    render(<Sidebar isOpen={true} pathname="/review" />)

    expect(screen.queryByText('Geography')).toBeNull()
    expect(screen.queryByText('Segment')).toBeNull()
    expect(screen.queryByText('Line of Business')).toBeNull()
    expect(screen.queryByText('Cost Center')).toBeNull()
  })

  it('hides dimension trees on chat page (pathname="/chat")', () => {
    render(<Sidebar isOpen={true} pathname="/chat" />)

    expect(screen.queryByText('Geography')).toBeNull()
    expect(screen.queryByText('Segment')).toBeNull()
    expect(screen.queryByText('Line of Business')).toBeNull()
    expect(screen.queryByText('Cost Center')).toBeNull()
  })
})
