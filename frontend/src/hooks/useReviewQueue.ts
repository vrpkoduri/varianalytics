import { useState, useMemo, useCallback } from 'react'
import { MOCK_REVIEW_DATA, type ReviewVariance } from '@/mocks/reviewData'

export function useReviewQueue(persona: string) {
  const [items, setItems] = useState<ReviewVariance[]>(MOCK_REVIEW_DATA)
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('varpct')
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set())

  const counts = useMemo(
    () => ({
      awaiting: items.filter((i) => i.status === 'draft').length,
      reviewed: items.filter((i) => i.status === 'reviewed').length,
      approved: items.filter((i) => i.status === 'approved').length,
      all: items.length,
    }),
    [items],
  )

  const filteredItems = useMemo(() => {
    let result = [...items]

    // Persona filter: BU Leader sees own BU only
    if (persona === 'bu') result = result.filter((i) => i.bu === 'Marsh')

    // Status filter
    if (statusFilter === 'awaiting') result = result.filter((i) => i.status === 'draft')
    else if (statusFilter !== 'all') result = result.filter((i) => i.status === statusFilter)

    // Search filter
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter((i) =>
        `${i.account} ${i.bu} ${i.geo}`.toLowerCase().includes(q),
      )
    }

    // Sort
    const sortFns: Record<string, (a: ReviewVariance, b: ReviewVariance) => number> = {
      varpct: (a, b) => Math.abs(b.variancePct) - Math.abs(a.variancePct),
      sla: (a, b) => b.sla - a.sla,
      account: (a, b) => a.account.localeCompare(b.account),
    }
    if (sortFns[sortBy]) result.sort(sortFns[sortBy])

    return result
  }, [items, persona, statusFilter, searchQuery, sortBy])

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }, [])

  const toggleCheck = useCallback((id: string) => {
    setCheckedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }, [])

  const batchMarkReviewed = useCallback(() => {
    setItems((prev) =>
      prev.map((item) =>
        checkedIds.has(item.id) && item.status === 'draft'
          ? { ...item, status: 'reviewed' as const }
          : item,
      ),
    )
    setCheckedIds(new Set())
  }, [checkedIds])

  const updateItemStatus = useCallback(
    (id: string, status: ReviewVariance['status']) => {
      setItems((prev) =>
        prev.map((item) => (item.id === id ? { ...item, status } : item)),
      )
    },
    [],
  )

  const updateHypothesisFeedback = useCallback(
    (itemId: string, hyIndex: number, feedback: -1 | 0 | 1) => {
      setItems((prev) =>
        prev.map((item) => {
          if (item.id !== itemId) return item
          const newHy = [...item.hypotheses]
          newHy[hyIndex] = { ...newHy[hyIndex], feedback }
          return { ...item, hypotheses: newHy }
        }),
      )
    },
    [],
  )

  const cycleSortBy = useCallback(() => {
    setSortBy((prev) =>
      prev === 'varpct' ? 'sla' : prev === 'sla' ? 'account' : 'varpct',
    )
  }, [])

  return {
    items: filteredItems,
    counts,
    statusFilter,
    setStatusFilter,
    sortBy,
    cycleSortBy,
    searchQuery,
    setSearchQuery,
    expandedIds,
    toggleExpand,
    checkedIds,
    toggleCheck,
    batchMarkReviewed,
    updateItemStatus,
    updateHypothesisFeedback,
  }
}
