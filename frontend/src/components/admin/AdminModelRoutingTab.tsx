/**
 * AI Agent Model Routing configuration editor tab.
 * Reads from and writes to /api/v1/config/model-routing.
 * Includes provider selector (Anthropic / Azure OpenAI).
 *
 * Phase 3E: Renamed from "LLM Model Routing" to "AI Agent Model Routing".
 */

import { useCallback, useEffect, useState } from 'react'
import { api } from '@/utils/api'

interface ModelRoute {
  task: string
  model: string
  maxTokens: number
  temperature: number
}

const PROVIDERS = [
  { value: 'anthropic', label: 'Anthropic (Claude)' },
  { value: 'azure', label: 'Azure OpenAI (GPT-4)' },
]

export function AdminModelRoutingTab() {
  const [routes, setRoutes] = useState<ModelRoute[]>([])
  const [provider, setProvider] = useState('anthropic')
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    api.gateway.get<{ routes: ModelRoute[]; provider?: string }>('/config/model-routing')
      .then((data) => {
        setRoutes(data.routes || [])
        if (data.provider) setProvider(data.provider)
      })
      .catch(() => {
        setRoutes([
          { task: 'narrative_generation', model: 'anthropic/claude-sonnet-4-20250514', maxTokens: 2048, temperature: 0.3 },
          { task: 'intent_classification', model: 'anthropic/claude-haiku-3-20250414', maxTokens: 256, temperature: 0.0 },
          { task: 'hypothesis_generation', model: 'anthropic/claude-sonnet-4-20250514', maxTokens: 1000, temperature: 0.3 },
          { task: 'embedding', model: 'text-embedding-3-small', maxTokens: 0, temperature: 0 },
        ])
      })
  }, [])

  const updateRoute = useCallback((idx: number, field: keyof ModelRoute, value: string | number) => {
    setRoutes((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, [field]: value } : r))
    )
  }, [])

  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      await api.gateway.put('/config/model-routing', {
        provider,
        routes: routes.map((r) => ({
          task: r.task,
          model: r.model,
          max_tokens: r.maxTokens,
          temperature: r.temperature,
        })),
      })
      setToast('AI Agent routing saved')
      setTimeout(() => setToast(null), 3000)
    } catch {
      setToast('Failed to save')
      setTimeout(() => setToast(null), 3000)
    } finally {
      setSaving(false)
    }
  }, [routes, provider])

  return (
    <div className="glass-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="section-label">AI AGENT MODEL ROUTING</span>
        {toast && (
          <span className={`text-[10px] px-2 py-1 rounded ${toast.includes('saved') ? 'bg-emerald/10 text-emerald' : 'bg-coral/10 text-coral'}`}>
            {toast}
          </span>
        )}
      </div>

      {/* Provider Selector */}
      <div className="p-3 rounded-lg bg-surface/50 border border-accent/20">
        <div className="flex items-center gap-4">
          <label className="text-[10px] text-text-secondary font-semibold uppercase tracking-wider">
            AI Provider
          </label>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="flex-1 px-3 py-1.5 rounded-lg bg-surface border border-border text-text text-[11px] focus:outline-none focus:ring-1 focus:ring-accent/50"
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Model Routes */}
      <div className="space-y-3">
        {routes.map((route, idx) => (
          <div key={route.task} className="p-3 rounded-lg bg-surface/50 border border-border/30 space-y-2">
            <div className="text-[10px] font-semibold text-accent uppercase tracking-wider">
              {route.task.replace(/_/g, ' ')}
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-[8px] text-text-secondary mb-0.5">Model</label>
                <input
                  type="text"
                  value={route.model}
                  onChange={(e) => updateRoute(idx, 'model', e.target.value)}
                  className="w-full px-2 py-1 rounded bg-surface border border-border text-text text-[11px] font-mono focus:outline-none focus:ring-1 focus:ring-accent/50"
                />
              </div>
              <div>
                <label className="block text-[8px] text-text-secondary mb-0.5">Max Tokens</label>
                <input
                  type="number"
                  value={route.maxTokens}
                  onChange={(e) => updateRoute(idx, 'maxTokens', parseInt(e.target.value) || 0)}
                  className="w-full px-2 py-1 rounded bg-surface border border-border text-text text-[11px] font-display focus:outline-none focus:ring-1 focus:ring-accent/50"
                />
              </div>
              <div>
                <label className="block text-[8px] text-text-secondary mb-0.5">Temperature</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={route.temperature}
                  onChange={(e) => updateRoute(idx, 'temperature', parseFloat(e.target.value) || 0)}
                  className="w-full px-2 py-1 rounded bg-surface border border-border text-text text-[11px] font-display focus:outline-none focus:ring-1 focus:ring-accent/50"
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-1.5 rounded-lg text-[11px] font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, var(--cobalt), var(--accent))' }}
        >
          {saving ? 'Saving...' : 'Save AI Agent Routing'}
        </button>
      </div>
    </div>
  )
}
