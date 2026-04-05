/**
 * Engine Control tab — run variance engine from the Admin panel.
 *
 * Features:
 * - Period / process / mode selectors
 * - Live cost estimate
 * - Run button with progress tracking
 * - Task history table
 * - Cancel running tasks
 *
 * Phase 3D.
 */

import { useCallback, useEffect, useState } from 'react'
import { useEngineControl } from '@/hooks/useEngineControl'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'

type Process = 'a' | 'b' | 'full'
type Mode = 'template' | 'llm'

export function AdminEngineControlTab() {
  const { filters } = useGlobalFilters()
  const period = filters.period
    ? `${filters.period.year}-${String(filters.period.month).padStart(2, '0')}`
    : '2026-06'

  const [selectedPeriod, setSelectedPeriod] = useState(period)
  const [selectedProcess, setSelectedProcess] = useState<Process>('full')
  const [selectedMode, setSelectedMode] = useState<Mode>('template')
  const [multiPeriod, setMultiPeriod] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const {
    estimate,
    currentTask,
    history,
    loading,
    error,
    fetchEstimate,
    runEngine,
    cancelTask,
    refreshHistory,
  } = useEngineControl()

  // Fetch estimate when config changes
  useEffect(() => {
    fetchEstimate({
      periodId: selectedPeriod,
      process: selectedProcess,
      mode: selectedMode,
      multiPeriod,
    })
  }, [selectedPeriod, selectedProcess, selectedMode, multiPeriod, fetchEstimate])

  const handleRun = useCallback(async () => {
    await runEngine({
      periodId: selectedPeriod,
      process: selectedProcess,
      mode: selectedMode,
      multiPeriod,
    })
    setToast('Engine task submitted')
    setTimeout(() => setToast(null), 3000)
  }, [selectedPeriod, selectedProcess, selectedMode, multiPeriod, runEngine])

  const handleCancel = useCallback(async () => {
    await cancelTask()
    setToast('Task cancelled')
    setTimeout(() => setToast(null), 3000)
  }, [cancelTask])

  const isRunning = currentTask?.status === 'running' || currentTask?.status === 'queued'

  return (
    <div className="space-y-6">
      {/* Config Section */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-tx-primary mb-4">Engine Configuration</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Period */}
          <div>
            <label className="block text-xs text-tx-secondary mb-1">Period</label>
            <input
              type="text"
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-tx-primary text-sm focus:border-teal focus:outline-none"
              placeholder="2026-06"
            />
          </div>

          {/* Process */}
          <div>
            <label className="block text-xs text-tx-secondary mb-1">Process</label>
            <select
              value={selectedProcess}
              onChange={(e) => setSelectedProcess(e.target.value as Process)}
              className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-tx-primary text-sm focus:border-teal focus:outline-none"
            >
              <option value="full">Full Pipeline</option>
              <option value="a">Process A (Math)</option>
              <option value="b">Process B (Narratives)</option>
            </select>
          </div>

          {/* Mode */}
          <div>
            <label className="block text-xs text-tx-secondary mb-1">Mode</label>
            <select
              value={selectedMode}
              onChange={(e) => setSelectedMode(e.target.value as Mode)}
              className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-tx-primary text-sm focus:border-teal focus:outline-none"
              disabled={selectedProcess === 'a'}
            >
              <option value="template">Template</option>
              <option value="llm">AI Agent</option>
            </select>
          </div>

          {/* Multi-period */}
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm text-tx-secondary cursor-pointer">
              <input
                type="checkbox"
                checked={multiPeriod}
                onChange={(e) => setMultiPeriod(e.target.checked)}
                className="w-4 h-4 rounded border-border bg-surface text-teal focus:ring-teal"
              />
              Multi-period (12 months)
            </label>
          </div>
        </div>
      </div>

      {/* Cost Estimate */}
      {estimate && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-tx-primary mb-3">Cost Estimate</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-teal">
                {estimate.estimatedCalls?.toLocaleString() ?? 0}
              </div>
              <div className="text-xs text-tx-secondary">AI Agent Calls</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-emerald">
                ${(estimate.estimatedCostUsd ?? 0).toFixed(2)}
              </div>
              <div className="text-xs text-tx-secondary">Estimated Cost</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-amber">
                {(estimate.estimatedTimeMinutes ?? 0).toFixed(1)} min
              </div>
              <div className="text-xs text-tx-secondary">Estimated Time</div>
            </div>
          </div>
          {estimate.note && (
            <p className="mt-3 text-xs text-tx-secondary text-center">{estimate.note}</p>
          )}
        </div>
      )}

      {/* Run Controls */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between">
          <button
            onClick={handleRun}
            disabled={isRunning || loading}
            className="px-6 py-2.5 bg-gradient-to-r from-teal to-persian text-white font-semibold rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isRunning ? 'Running...' : '▶ Run Engine'}
          </button>

          {isRunning && (
            <button
              onClick={handleCancel}
              className="px-4 py-2 border border-coral/30 text-coral rounded-lg hover:bg-coral/10 transition-all"
            >
              Cancel
            </button>
          )}
        </div>

        {/* Progress */}
        {currentTask && isRunning && (
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-tx-secondary">{currentTask.currentPass || 'Starting...'}</span>
              <span className="text-teal">{Math.round((currentTask.progress ?? 0) * 100)}%</span>
            </div>
            <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-teal to-persian rounded-full transition-all duration-500"
                style={{ width: `${Math.max((currentTask.progress ?? 0) * 100, 2)}%` }}
              />
            </div>
          </div>
        )}

        {/* Completion message */}
        {currentTask && currentTask.status === 'completed' && (
          <div className="mt-4 p-3 bg-emerald/10 border border-emerald/20 rounded-lg">
            <p className="text-sm text-emerald">
              Engine run completed in {currentTask.actualResult?.totalTimeSeconds?.toFixed(1) ?? '?'}s
              — {currentTask.actualResult?.materialVariances?.toLocaleString() ?? '?'} material variances processed
            </p>
          </div>
        )}

        {currentTask && currentTask.status === 'failed' && (
          <div className="mt-4 p-3 bg-coral/10 border border-coral/20 rounded-lg">
            <p className="text-sm text-coral">
              Engine run failed: {currentTask.error || 'Unknown error'}
            </p>
          </div>
        )}
      </div>

      {/* Run History */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-tx-primary">Run History</h3>
          <button
            onClick={refreshHistory}
            className="text-xs text-teal hover:opacity-80 transition-colors"
          >
            Refresh
          </button>
        </div>

        {history.length === 0 ? (
          <p className="text-sm text-tx-tertiary text-center py-4">No engine runs yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-tx-secondary text-xs border-b border-border">
                  <th className="text-left py-2 px-2">ID</th>
                  <th className="text-left py-2 px-2">Period</th>
                  <th className="text-left py-2 px-2">Process</th>
                  <th className="text-left py-2 px-2">Mode</th>
                  <th className="text-right py-2 px-2">Time</th>
                  <th className="text-center py-2 px-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {history.map((task: any) => (
                  <tr key={task.taskId} className="border-b border-border/30 hover:bg-surface/50">
                    <td className="py-2 px-2 text-tx-secondary font-mono text-xs">{task.taskId}</td>
                    <td className="py-2 px-2 text-tx-primary">{task.periodId}</td>
                    <td className="py-2 px-2 text-tx-secondary">
                      {task.process === 'a' ? 'A (Math)' : task.process === 'b' ? 'B (Narr)' : 'Full'}
                    </td>
                    <td className="py-2 px-2 text-tx-secondary capitalize">{task.mode}</td>
                    <td className="py-2 px-2 text-right text-tx-secondary">
                      {task.actualResult?.totalTimeSeconds
                        ? `${task.actualResult.totalTimeSeconds.toFixed(1)}s`
                        : '—'}
                    </td>
                    <td className="py-2 px-2 text-center">
                      <StatusBadge status={task.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Toast */}
      {(toast || error) && (
        <div className={`fixed bottom-4 right-4 px-4 py-2 rounded-lg text-sm shadow-lg text-white ${
          error ? 'bg-coral/90' : 'bg-teal/90'
        }`}>
          {error || toast}
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: 'text-emerald bg-emerald/10',
    running: 'text-teal bg-teal/10',
    queued: 'text-amber bg-amber/10',
    failed: 'text-coral bg-coral/10',
    cancelled: 'text-tx-tertiary bg-surface',
  }

  const icons: Record<string, string> = {
    completed: '✓',
    running: '◉',
    queued: '◌',
    failed: '✗',
    cancelled: '—',
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${colors[status] || 'text-tx-tertiary'}`}>
      {icons[status] || '?'} {status}
    </span>
  )
}
