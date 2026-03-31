/**
 * Shared hook for submitting review actions to the gateway API.
 * Used by: NarrativeSection, ActionButtons, HypothesisCards, useReviewQueue
 */
import { useCallback } from 'react'
import { api } from '@/utils/api'

export interface ReviewActionPayload {
  variance_id: string
  action: 'approve' | 'edit' | 'escalate' | 'dismiss' | 'director_approve' | 'director_reject'
  edited_narrative?: string
  hypothesis_feedback?: string
  comment?: string
}

export function useReviewAction() {
  const submitAction = useCallback(async (payload: ReviewActionPayload) => {
    try {
      const result = await api.gateway.post('/review/actions', payload)
      return result as { variance_id: string; new_status: string; message: string }
    } catch (error) {
      console.error('Review action failed:', error)
      return null
    }
  }, [])

  return { submitAction }
}
