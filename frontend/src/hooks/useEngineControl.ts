import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '@/utils/api'

interface CostEstimate {
  estimatedCalls: number
  estimatedCostUsd: number
  estimatedTimeMinutes: number
  mode: string
  process: string
  periods: number
  note?: string
  breakdown?: Record<string, number>
}

interface EngineTask {
  taskId: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  process: string
  mode: string
  periodId: string
  periods: string[]
  multiPeriod: boolean
  createdAt: string
  startedAt: string | null
  completedAt: string | null
  progress: number
  currentPass: string
  costEstimate: Record<string, any>
  actualResult: Record<string, any> | null
  error: string | null
}

interface EngineConfig {
  periodId: string
  process: 'a' | 'b' | 'full'
  mode: 'template' | 'llm'
  multiPeriod: boolean
}

export function useEngineControl() {
  const [estimate, setEstimate] = useState<CostEstimate | null>(null)
  const [currentTask, setCurrentTask] = useState<EngineTask | null>(null)
  const [history, setHistory] = useState<EngineTask[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Fetch cost estimate
  const fetchEstimate = useCallback(async (config: EngineConfig) => {
    try {
      const est = await api.computation.post<CostEstimate>('/engine/estimate', {
        period_id: config.periodId,
        process: config.process,
        mode: config.mode,
        multi_period: config.multiPeriod,
      })
      setEstimate(est)
      setError(null)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch estimate')
    }
  }, [])

  // Submit engine run
  const runEngine = useCallback(async (config: EngineConfig) => {
    setLoading(true)
    setError(null)
    try {
      const task = await api.computation.post<EngineTask>('/engine/run', {
        period_id: config.periodId,
        process: config.process,
        mode: config.mode,
        multi_period: config.multiPeriod,
      })
      setCurrentTask(task)
      startPolling(task.taskId)
    } catch (err: any) {
      setError(err.message || 'Failed to start engine run')
      setLoading(false)
    }
  }, [])

  // Cancel running task
  const cancelTask = useCallback(async () => {
    if (!currentTask) return
    try {
      await api.computation.post(`/engine/tasks/${currentTask.taskId}/cancel`, {})
      stopPolling()
      setCurrentTask(prev => prev ? { ...prev, status: 'cancelled' } : null)
      setLoading(false)
      refreshHistory()
    } catch (err: any) {
      setError(err.message || 'Failed to cancel task')
    }
  }, [currentTask])

  // Refresh task history
  const refreshHistory = useCallback(async () => {
    try {
      const tasks = await api.computation.get<EngineTask[]>('/engine/tasks?limit=20')
      setHistory(tasks || [])
    } catch {
      // Silently fail — history is non-critical
    }
  }, [])

  // Polling for task progress
  const startPolling = useCallback((taskId: string) => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const updated = await api.computation.get<EngineTask>(`/engine/tasks/${taskId}`)
        setCurrentTask(updated)
        if (updated.status !== 'running' && updated.status !== 'queued') {
          stopPolling()
          setLoading(false)
          refreshHistory()
        }
      } catch {
        stopPolling()
        setLoading(false)
      }
    }, 2000)
  }, [refreshHistory])

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  // Load history on mount
  useEffect(() => {
    refreshHistory()
    return () => stopPolling()
  }, [])

  return {
    estimate,
    currentTask,
    history,
    loading,
    error,
    fetchEstimate,
    runEngine,
    cancelTask,
    refreshHistory,
  }
}
