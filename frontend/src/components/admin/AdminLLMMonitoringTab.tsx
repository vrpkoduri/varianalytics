/**
 * AI Monitoring tab — LLM health, narrative quality, model routing, engine history.
 * Fetches from /admin/llm-health, /admin/narrative-quality, /admin/llm-test.
 */

import { useCallback, useEffect, useState } from 'react'
import { api } from '@/utils/api'

interface LLMHealth {
  status: string
  provider: string
  endpoint: string
  apiKeyConfigured: boolean
  models: Array<{ task: string; model: string; costInputPer1m: number; costOutputPer1m: number }>
}

interface NarrativeQuality {
  total: number
  llmCount: number
  templateCount: number
  llmPct: number
  byLevel: Record<string, { populated: number; total: number; pct: number }>
  engineRuns: Array<{
    runId: string
    periodId: string
    method: string
    llmGenerated: number
    templateGenerated: number
    timestamp: string
  }>
}

interface TestResult {
  success: boolean
  provider: string
  model: string
  responseText: string
  latencyMs: number
  tokens: { prompt: number; completion: number; total: number }
}

export function AdminLLMMonitoringTab() {
  const [health, setHealth] = useState<LLMHealth | null>(null)
  const [quality, setQuality] = useState<NarrativeQuality | null>(null)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [testing, setTesting] = useState(false)
  const [loading, setLoading] = useState(true)

  // Fetch health + quality on mount
  useEffect(() => {
    Promise.all([
      api.gateway.get<LLMHealth>('/admin/llm-health').catch(() => null),
      api.gateway.get<NarrativeQuality>('/admin/narrative-quality').catch(() => null),
    ]).then(([h, q]) => {
      if (h) setHealth(h)
      if (q) setQuality(q)
      setLoading(false)
    })
  }, [])

  const runTest = useCallback(async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await api.gateway.post<TestResult>('/admin/llm-test', {})
      setTestResult(result)
    } catch {
      setTestResult({
        success: false,
        provider: 'error',
        model: '',
        responseText: 'Failed to reach API',
        latencyMs: 0,
        tokens: { prompt: 0, completion: 0, total: 0 },
      })
    } finally {
      setTesting(false)
    }
  }, [])

  if (loading) {
    return (
      <div className="glass-card p-6 text-center text-tx-tertiary text-[11px]">
        Loading AI monitoring data...
      </div>
    )
  }

  const statusColor = health?.status === 'healthy' ? 'text-emerald' : 'text-coral'
  const statusDot = health?.status === 'healthy' ? 'bg-emerald' : 'bg-coral'

  return (
    <div className="space-y-3">
      {/* LLM Status */}
      <div className="glass-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="section-label">LLM STATUS</span>
          <button
            onClick={runTest}
            disabled={testing}
            className="px-3 py-1 rounded-lg text-[10px] font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, var(--cobalt), var(--accent))' }}
          >
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-2.5 rounded-lg bg-surface/50 border border-border/30">
            <div className="text-[8px] text-tx-tertiary uppercase tracking-wider mb-1">Provider</div>
            <div className="text-[12px] font-semibold text-tx-primary capitalize">{health?.provider || 'Not configured'}</div>
          </div>
          <div className="p-2.5 rounded-lg bg-surface/50 border border-border/30">
            <div className="text-[8px] text-tx-tertiary uppercase tracking-wider mb-1">Status</div>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${statusDot}`} />
              <span className={`text-[12px] font-semibold capitalize ${statusColor}`}>
                {health?.status || 'Unknown'}
              </span>
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-surface/50 border border-border/30">
            <div className="text-[8px] text-tx-tertiary uppercase tracking-wider mb-1">API Key</div>
            <div className="text-[12px] font-semibold text-tx-primary">
              {health?.apiKeyConfigured ? '\u2713 Configured' : '\u2717 Missing'}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-surface/50 border border-border/30">
            <div className="text-[8px] text-tx-tertiary uppercase tracking-wider mb-1">Endpoint</div>
            <div className="text-[10px] font-mono text-tx-secondary truncate" title={health?.endpoint}>
              {health?.endpoint ? health.endpoint.replace(/https?:\/\//, '').split('/')[0] : 'Not set'}
            </div>
          </div>
        </div>

        {/* Test Result */}
        {testResult && (
          <div className={`p-3 rounded-lg border ${testResult.success ? 'border-emerald/30 bg-emerald/5' : 'border-coral/30 bg-coral/5'}`}>
            <div className="flex items-center justify-between mb-1.5">
              <span className={`text-[10px] font-semibold ${testResult.success ? 'text-emerald' : 'text-coral'}`}>
                {testResult.success ? '\u2713 Connection Successful' : '\u2717 Connection Failed'}
              </span>
              <span className="text-[9px] text-tx-tertiary">
                {testResult.latencyMs}ms | {testResult.tokens.total} tokens | {testResult.model.split('/').pop()}
              </span>
            </div>
            <div className="text-[10px] text-tx-secondary italic">
              "{testResult.responseText}"
            </div>
          </div>
        )}
      </div>

      {/* Narrative Quality */}
      <div className="glass-card p-4 space-y-3">
        <span className="section-label">NARRATIVE QUALITY</span>

        {quality && quality.total > 0 ? (
          <>
            {/* Overall bar */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-tx-secondary">AI-Generated: {quality.llmCount} ({quality.llmPct}%)</span>
                <span className="text-tx-tertiary">Template: {quality.templateCount} ({(100 - quality.llmPct).toFixed(1)}%)</span>
              </div>
              <div className="h-3 rounded-full bg-surface/80 overflow-hidden flex">
                <div
                  className="h-full bg-gradient-to-r from-teal to-emerald rounded-l-full transition-all duration-500"
                  style={{ width: `${quality.llmPct}%` }}
                />
                <div
                  className="h-full bg-gold/40 rounded-r-full transition-all duration-500"
                  style={{ width: `${100 - quality.llmPct}%` }}
                />
              </div>
              <div className="text-[9px] text-tx-tertiary">
                {quality.total} total material variances
              </div>
            </div>

            {/* By level */}
            <div className="space-y-2 mt-3">
              <div className="text-[9px] font-semibold text-tx-tertiary uppercase tracking-wider">By Narrative Level</div>
              {Object.entries(quality.byLevel).map(([level, data]) => (
                <div key={level} className="flex items-center gap-3">
                  <span className="text-[10px] text-tx-secondary w-20 capitalize">{level}</span>
                  <div className="flex-1 h-2 rounded-full bg-surface/80 overflow-hidden">
                    <div
                      className="h-full bg-teal/60 rounded-full transition-all duration-500"
                      style={{ width: `${data.pct}%` }}
                    />
                  </div>
                  <span className="text-[9px] text-tx-tertiary w-24 text-right">
                    {data.populated}/{data.total} ({data.pct}%)
                  </span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="text-[10px] text-tx-tertiary">No narrative data available. Run the engine first.</div>
        )}
      </div>

      {/* Model Routing */}
      <div className="glass-card p-4 space-y-3">
        <span className="section-label">MODEL ROUTING</span>
        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-tx-tertiary text-left uppercase tracking-wider">
                <th className="pb-2 font-semibold">Task</th>
                <th className="pb-2 font-semibold">Model</th>
                <th className="pb-2 font-semibold text-right">Cost (Input/1M)</th>
                <th className="pb-2 font-semibold text-right">Cost (Output/1M)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/20">
              {(health?.models || []).map((m) => (
                <tr key={m.task} className="text-tx-secondary">
                  <td className="py-1.5 capitalize">{m.task.replace(/_/g, ' ')}</td>
                  <td className="py-1.5 font-mono text-[9px] text-teal">
                    {m.model.split('/').pop()}
                  </td>
                  <td className="py-1.5 text-right">${(m.costInputPer1m ?? 0).toFixed(2)}</td>
                  <td className="py-1.5 text-right">${(m.costOutputPer1m ?? 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Engine Run History */}
      {quality && quality.engineRuns.length > 0 && (
        <div className="glass-card p-4 space-y-3">
          <span className="section-label">ENGINE RUN HISTORY</span>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="text-tx-tertiary text-left uppercase tracking-wider">
                  <th className="pb-2 font-semibold">Run ID</th>
                  <th className="pb-2 font-semibold">Period</th>
                  <th className="pb-2 font-semibold">Method</th>
                  <th className="pb-2 font-semibold text-right">LLM</th>
                  <th className="pb-2 font-semibold text-right">Template</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/20">
                {quality.engineRuns.map((run, i) => (
                  <tr key={i} className="text-tx-secondary">
                    <td className="py-1.5 font-mono text-[9px]">{run.runId}...</td>
                    <td className="py-1.5">{run.periodId}</td>
                    <td className="py-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-[8px] font-semibold ${
                        run.method.includes('llm') ? 'bg-emerald/10 text-emerald' : 'bg-gold/10 text-gold'
                      }`}>
                        {run.method}
                      </span>
                    </td>
                    <td className="py-1.5 text-right text-emerald">{run.llmGenerated}</td>
                    <td className="py-1.5 text-right text-gold">{run.templateGenerated}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
