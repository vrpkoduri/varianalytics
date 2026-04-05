/**
 * useApprovalQueue — persona propagation tests.
 *
 * Verifies that the hook:
 *  1. Passes persona to the API query string
 *  2. Re-fetches when persona changes
 *  3. Does NOT do client-side BU filtering
 *  4. Falls back to MOCK_APPROVAL_DATA on API error
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useApprovalQueue } from '../useApprovalQueue'

// ---- Mocks ----

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('@/utils/api', () => ({
  api: {
    gateway: {
      get: (...args: any[]) => mockGet(...args),
      post: (...args: any[]) => mockPost(...args),
    },
  },
}))

vi.mock('@/utils/transformers', () => ({
  transformApprovalItems: (items: any[]) => items,
}))

// Mock confetti so it doesn't error in jsdom
vi.mock('@/components/common/ConfettiContainer', () => ({
  fireConfetti: vi.fn(),
}))

// Real mock data for fallback assertion
const MOCK_APPROVAL_DATA_MODULE = await import('@/mocks/approvalData')

// ---- Helpers ----

function makeItem(overrides: Record<string, any> = {}) {
  return {
    id: 'a-1',
    account: 'Advisory Fees',
    bu: 'Marsh',
    geo: 'APAC',
    variance: 6900,
    variancePct: 15.3,
    favorable: true,
    status: 'reviewed',
    assignedAnalyst: 'Sarah Chen',
    isEdited: false,
    ...overrides,
  }
}

// ---- Tests ----

describe('useApprovalQueue persona propagation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches with persona param in the URL', async () => {
    const items = [makeItem()]
    mockGet.mockResolvedValue({ items })

    renderHook(() => useApprovalQueue('director'))

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledTimes(1)
    })

    const url: string = mockGet.mock.calls[0][0]
    expect(url).toContain('persona=director')
  })

  it('re-fetches when persona changes from analyst to cfo', async () => {
    const items = [makeItem()]
    mockGet.mockResolvedValue({ items })

    const { rerender } = renderHook(
      ({ persona }) => useApprovalQueue(persona),
      { initialProps: { persona: 'analyst' } },
    )

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledTimes(1)
    })

    // Change persona
    rerender({ persona: 'cfo' })

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledTimes(2)
    })

    const secondUrl: string = mockGet.mock.calls[1][0]
    expect(secondUrl).toContain('persona=cfo')
  })

  it('does not apply client-side BU filtering', async () => {
    // Return items from multiple BUs — all should appear regardless of persona
    const items = [
      makeItem({ id: 'a-1', bu: 'Marsh', assignedAnalyst: 'Sarah Chen' }),
      makeItem({ id: 'a-2', bu: 'Mercer', assignedAnalyst: 'Sarah Chen' }),
      makeItem({ id: 'a-3', bu: 'Guy Carpenter', assignedAnalyst: 'James Park' }),
    ]
    mockGet.mockResolvedValue({ items })

    const { result } = renderHook(() => useApprovalQueue('bu_leader'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Flatten all items from analyst groups
    const allItems = result.current.analystGroups.flatMap(
      (g: any) => g.items,
    )
    expect(allItems).toHaveLength(3)
    const bus = allItems.map((i: any) => i.bu)
    expect(bus).toContain('Marsh')
    expect(bus).toContain('Mercer')
    expect(bus).toContain('Guy Carpenter')
  })

  it('falls back to MOCK_APPROVAL_DATA on API error', async () => {
    mockGet.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useApprovalQueue('director'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.usingMock).toBe(true)
    // analystGroups should be populated from mock data
    const allItems = result.current.analystGroups.flatMap(
      (g: any) => g.items,
    )
    expect(allItems.length).toBeGreaterThan(0)
    expect(allItems[0].id).toBe(
      MOCK_APPROVAL_DATA_MODULE.MOCK_APPROVAL_DATA[0].id,
    )
  })
})
