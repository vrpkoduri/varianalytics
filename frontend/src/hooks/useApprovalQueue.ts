import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  MOCK_APPROVAL_DATA,
  type ApprovalVariance,
  type AnalystGroupData,
} from '../mocks/approvalData'
import { fireConfetti } from '../components/common/ConfettiContainer'
import { api } from '../utils/api'
import { transformApprovalItems } from '../utils/transformers'

export function useApprovalQueue() {
  const [items, setItems] = useState<ApprovalVariance[]>([])
  const [usingMock, setUsingMock] = useState(false)
  const [loading, setLoading] = useState(true)

  // Fetch from API, fallback to mock
  useEffect(() => {
    setLoading(true)
    api.gateway
      .get('/approval/queue?page_size=50')
      .then((data: any) => {
        const queueItems = data.items || data
        if (Array.isArray(queueItems) && queueItems.length > 0) {
          setItems(transformApprovalItems(queueItems))
          setUsingMock(false)
        } else {
          setItems(MOCK_APPROVAL_DATA)
          setUsingMock(true)
        }
        setLoading(false)
      })
      .catch(() => {
        setItems(MOCK_APPROVAL_DATA)
        setUsingMock(true)
        setLoading(false)
      })
  }, [])

  const pendingCount = useMemo(
    () => items.filter((i) => i.status !== 'approved').length,
    [items],
  )

  const analystGroups = useMemo((): AnalystGroupData[] => {
    const groups: Record<string, ApprovalVariance[]> = {}
    items.forEach((item) => {
      const analyst = item.assignedAnalyst
      ;(groups[analyst] ??= []).push(item)
    })
    return Object.entries(groups).map(([name, groupItems]) => ({
      name,
      initials: name
        .split(' ')
        .map((w) => w[0])
        .join(''),
      items: groupItems,
    }))
  }, [items])

  const approveItem = useCallback(
    (id: string) => {
      if (!usingMock) {
        api.gateway
          .post('/approval/actions', {
            variance_ids: [id],
            action: 'approve',
          })
          .then(() => {
            api.gateway.get('/approval/queue?page_size=50').then((data: any) => {
              const queueItems = data.items || data
              if (Array.isArray(queueItems)) setItems(transformApprovalItems(queueItems))
            })
          })
          .catch(() => {
            // Fallback to local state
            setItems((prev) =>
              prev.map((item) =>
                item.id === id
                  ? { ...item, status: 'approved' as const }
                  : item,
              ),
            )
          })
      } else {
        setItems((prev) =>
          prev.map((item) =>
            item.id === id ? { ...item, status: 'approved' as const } : item,
          ),
        )
      }
      fireConfetti()
    },
    [usingMock],
  )

  const refreshQueue = useCallback(() => {
    api.gateway.get('/approval/queue?page_size=50').then((data: any) => {
      const queueItems = data.items || data
      if (Array.isArray(queueItems)) setItems(transformApprovalItems(queueItems))
    }).catch(() => {})
  }, [])

  const holdItem = useCallback((id: string) => {
    if (usingMock) {
      // In mock mode, item stays in reviewed state — no change needed
      return
    }
    api.gateway
      .post('/approval/actions', {
        variance_ids: [id],
        action: 'reject',
        comment: 'Held for further review',
      })
      .then(() => refreshQueue())
      .catch(() => {})
  }, [usingMock, refreshQueue])

  const approveAllReviewed = useCallback(() => {
    if (!usingMock) {
      const reviewedIds = items
        .filter((i) => i.status === 'reviewed')
        .map((i) => i.id)
      if (reviewedIds.length > 0) {
        api.gateway
          .post('/approval/actions', {
            variance_ids: reviewedIds,
            action: 'approve',
          })
          .then(() => {
            api.gateway.get('/approval/queue?page_size=50').then((data: any) => {
              const queueItems = data.items || data
              if (Array.isArray(queueItems)) setItems(transformApprovalItems(queueItems))
            })
          })
          .catch(() => {
            setItems((prev) =>
              prev.map((item) =>
                item.status === 'reviewed'
                  ? { ...item, status: 'approved' as const }
                  : item,
              ),
            )
          })
      }
    } else {
      setItems((prev) =>
        prev.map((item) =>
          item.status === 'reviewed'
            ? { ...item, status: 'approved' as const }
            : item,
        ),
      )
    }
    fireConfetti()
  }, [items, usingMock])

  const bulkApproveGroup = useCallback(
    (analystName: string) => {
      if (!usingMock) {
        const groupIds = items
          .filter(
            (i) =>
              i.assignedAnalyst === analystName && i.status === 'reviewed',
          )
          .map((i) => i.id)
        if (groupIds.length > 0) {
          api.gateway
            .post('/approval/actions', {
              variance_ids: groupIds,
              action: 'approve',
            })
            .then(() => {
              api.gateway
                .get('/approval/queue?page_size=50')
                .then((data: any) => {
                  const queueItems = data.items || data
                  if (Array.isArray(queueItems)) setItems(queueItems)
                })
            })
            .catch(() => {
              setItems((prev) =>
                prev.map((item) =>
                  item.assignedAnalyst === analystName &&
                  item.status === 'reviewed'
                    ? { ...item, status: 'approved' as const }
                    : item,
                ),
              )
            })
        }
      } else {
        setItems((prev) =>
          prev.map((item) =>
            item.assignedAnalyst === analystName && item.status === 'reviewed'
              ? { ...item, status: 'approved' as const }
              : item,
          ),
        )
      }
      fireConfetti()
    },
    [items, usingMock],
  )

  return {
    analystGroups,
    pendingCount,
    approveItem,
    holdItem,
    approveAllReviewed,
    bulkApproveGroup,
    loading,
    usingMock,
  }
}
