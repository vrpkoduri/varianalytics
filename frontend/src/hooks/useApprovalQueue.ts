import { useState, useMemo, useCallback } from 'react'
import { MOCK_APPROVAL_DATA, type ApprovalVariance, type AnalystGroupData } from '../mocks/approvalData'
import { fireConfetti } from '../components/common/ConfettiContainer'

export function useApprovalQueue() {
  const [items, setItems] = useState<ApprovalVariance[]>(MOCK_APPROVAL_DATA)

  const pendingCount = useMemo(() =>
    items.filter(i => i.status !== 'approved').length
  , [items])

  const analystGroups = useMemo((): AnalystGroupData[] => {
    const groups: Record<string, ApprovalVariance[]> = {}
    items.forEach(item => {
      const analyst = item.assignedAnalyst
      ;(groups[analyst] ??= []).push(item)
    })
    return Object.entries(groups).map(([name, groupItems]) => ({
      name,
      initials: name.split(' ').map(w => w[0]).join(''),
      items: groupItems,
    }))
  }, [items])

  const approveItem = useCallback((id: string) => {
    setItems(prev => prev.map(item =>
      item.id === id ? { ...item, status: 'approved' as const } : item
    ))
    fireConfetti()
  }, [])

  const holdItem = useCallback((_id: string) => {
    // Hold keeps status as 'reviewed' (no change in this simple mock)
    // In production, this would set a hold flag or revert to draft
  }, [])

  const approveAllReviewed = useCallback(() => {
    setItems(prev => prev.map(item =>
      item.status === 'reviewed' ? { ...item, status: 'approved' as const } : item
    ))
    fireConfetti()
  }, [])

  const bulkApproveGroup = useCallback((analystName: string) => {
    setItems(prev => prev.map(item =>
      item.assignedAnalyst === analystName && item.status === 'reviewed'
        ? { ...item, status: 'approved' as const }
        : item
    ))
    fireConfetti()
  }, [])

  return { analystGroups, pendingCount, approveItem, holdItem, approveAllReviewed, bulkApproveGroup }
}
