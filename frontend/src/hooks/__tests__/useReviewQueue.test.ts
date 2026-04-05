/**
 * useReviewQueue — persona propagation tests.
 *
 * Verifies that the hook:
 *  1. Passes persona to the API query string
 *  2. Re-fetches when persona changes
 *  3. Does NOT do client-side BU filtering
 *  4. Falls back to MOCK_REVIEW_DATA on API error
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useReviewQueue } from '../useReviewQueue'

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
  transformReviewItems: (items: any[]) => items,
}))

// We need the real MOCK_REVIEW_DATA for fallback assertion
const MOCK_REVIEW_DATA_MODULE = await import('@/mocks/reviewData')

// ---- Helpers ----

function makeItem(overrides: Record<string, any> = {}) {
  return {
    id: 'r-1',
    account: 'Revenue',
    bu: 'Marsh',
    geo: 'Americas',
    variance: 1200,
    variancePct: 8.5,
    favorable: true,
    type: 'material',
    status: 'draft',
    sla: 12,
    sparkData: [1, 2, 3],
    isEdited: false,
    isSynthesized: false,
    narratives: { detail: '', midlevel: '', summary: '', board: '' },
    decomposition: [],
    hypotheses: [],
    ...overrides,
  }
}

// ---- Tests ----

describe('useReviewQueue persona propagation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches with persona param in the URL', async () => {
    const items = [makeItem()]
    mockGet.mockResolvedValue({ items })

    renderHook(() => useReviewQueue('analyst'))

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledTimes(1)
    })

    const url: string = mockGet.mock.calls[0][0]
    expect(url).toContain('persona=analyst')
  })

  it('re-fetches when persona changes from analyst to cfo', async () => {
    const items = [makeItem()]
    mockGet.mockResolvedValue({ items })

    const { rerender } = renderHook(
      ({ persona }) => useReviewQueue(persona),
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
      makeItem({ id: 'r-1', bu: 'Marsh' }),
      makeItem({ id: 'r-2', bu: 'Mercer' }),
      makeItem({ id: 'r-3', bu: 'Guy Carpenter' }),
    ]
    mockGet.mockResolvedValue({ items })

    const { result } = renderHook(() => useReviewQueue('bu_leader'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // All 3 items returned — no client-side BU filter removed any
    expect(result.current.items).toHaveLength(3)
    const bus = result.current.items.map((i: any) => i.bu)
    expect(bus).toContain('Marsh')
    expect(bus).toContain('Mercer')
    expect(bus).toContain('Guy Carpenter')
  })

  it('falls back to MOCK_REVIEW_DATA on API error', async () => {
    mockGet.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useReviewQueue('analyst'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.usingMock).toBe(true)
    expect(result.current.items.length).toBeGreaterThan(0)
    // Items come from mock data (may be re-sorted by default varpct sort)
    const mockIds = MOCK_REVIEW_DATA_MODULE.MOCK_REVIEW_DATA.map((i) => i.id)
    const returnedIds = result.current.items.map((i: any) => i.id)
    returnedIds.forEach((id: string) => {
      expect(mockIds).toContain(id)
    })
  })
})
