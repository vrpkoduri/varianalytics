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
        <h3 className="text-lg font-semibold text-white mb-4">Engine Configuration</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Period */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Period</label>
            <input
              type="text"
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:border-teal-400 focus:outline-none"
              placeholder="2026-06"
            />
          </div>

          {/* Process */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Process</label>
            <select
              value={selectedProcess}
              onChange={(e) => setSelectedProcess(e.target.value as Process)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:border-teal-400 focus:outline-none"
            >
              <option value="full">Full Pipeline</option>
              <option value="a">Process A (Math)</option>
              <option value="b">Process B (Narratives)</option>
            </select>
          </div>

          {/* Mode */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Mode</label>
            <select
              value={selectedMode}
              onChange={(e) => setSelectedMode(e.target.value as Mode)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:border-teal-400 focus:outline-none"
              disabled={selectedProcess === 'a'}
            >
              <option value="template">Template</option>
              <option value="llm">LLM</option>
            </select>
          </div>

          {/* Multi-period */}
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={multiPeriod}
                onChange={(e) => setMultiPeriod(e.target.checked)}
                className="w-4 h-4 rounded border-white/20 bg-white/5 text-teal-400 focus:ring-teal-400"
              />
              Multi-period (12 months)
            </label>
          </div>
        </div>
      </div>

      {/* Cost Estimate */}
      {estimate && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-3">Cost Estimate</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-teal-400">
                {estimate.estimatedCalls?.toLocaleString() ?? 0}
              </div>
              <div className="text-xs text-gray-400">LLM Calls</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-emerald-400">
                ${(estimate.estimatedCostUsd ?? 0).toFixed(2)}
              </div>
              <div className="text-xs text-gray-400">Estimated Cost</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-amber-400">
                {(estimate.estimatedTimeMinutes ?? 0).toFixed(1)} min
              </div>
              <div className="text-xs text-gray-400">Estimated Time</div>
            </div>
          </div>
          {estimate.note && (
            <p className="mt-3 text-xs text-gray-400 text-center">{estimate.note}</p>
          )}
        </div>
      )}

      {/* Run Controls */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between">
          <button
            onClick={handleRun}
            disabled={isRunning || loading}
            className="px-6 py-2.5 bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-semibold rounded-lg hover:from-teal-400 hover:to-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isRunning ? 'Running...' : '▶ Run Engine'}
          </button>

          {isRunning && (
            <button
              onClick={handleCancel}
              className="px-4 py-2 border border-red-500/30 text-red-400 rounded-lg hover:bg-red-500/10 transition-all"
            >
              Cancel
            </button>
          )}
        </div>

        {/* Progress */}
        {currentTask && isRunning && (
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-gray-300">{currentTask.currentPass || 'Starting...'}</span>
              <span className="text-teal-400">{Math.round((currentTask.progress ?? 0) * 100)}%</span>
            </div>
            <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-teal-500 to-cyan-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.max((currentTask.progress ?? 0) * 100, 2)}%` }}
              />
            </div>
          </div>
        )}

        {/* Completion message */}
        {currentTask && currentTask.status === 'completed' && (
          <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
            <p className="text-sm text-emerald-400">
              Engine run completed in {currentTask.actualResult?.totalTimeSeconds?.toFixed(1) ?? '?'}s
              — {currentTask.actualResult?.materialVariances?.toLocaleString() ?? '?'} material variances processed
            </p>
          </div>
        )}

        {currentTask && currentTask.status === 'failed' && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <p className="text-sm text-red-400">
              Engine run failed: {currentTask.error || 'Unknown error'}
            </p>
          </div>
        )}
      </div>

      {/* Run History */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Run History</h3>
          <button
            onClick={refreshHistory}
            className="text-xs text-teal-400 hover:text-teal-300 transition-colors"
          >
            Refresh
          </button>
        </div>

        {history.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">No engine runs yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 text-xs border-b border-white/10">
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
                  <tr key={task.taskId} className="border-b border-white/5 hover:bg-white/5">
                    <td className="py-2 px-2 text-gray-300 font-mono text-xs">{task.taskId}</td>
                    <td className="py-2 px-2 text-white">{task.periodId}</td>
                    <td className="py-2 px-2 text-gray-300">
                      {task.process === 'a' ? 'A (Math)' : task.process === 'b' ? 'B (Narr)' : 'Full'}
                    </td>
                    <td className="py-2 px-2 text-gray-300 capitalize">{task.mode}</td>
                    <td className="py-2 px-2 text-right text-gray-300">
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
        <div className={`fixed bottom-4 right-4 px-4 py-2 rounded-lg text-sm shadow-lg ${
          error ? 'bg-red-500/90 text-white' : 'bg-teal-500/90 text-white'
        }`}>
          {error || toast}
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: 'text-emerald-400 bg-emerald-400/10',
    running: 'text-teal-400 bg-teal-400/10',
    queued: 'text-amber-400 bg-amber-400/10',
    failed: 'text-red-400 bg-red-400/10',
    cancelled: 'text-gray-400 bg-gray-400/10',
  }

  const icons: Record<string, string> = {
    completed: '✓',
    running: '◉',
    queued: '◌',
    failed: '✗',
    cancelled: '—',
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${colors[status] || 'text-gray-400'}`}>
      {icons[status] || '?'} {status}
    </span>
  )
}
