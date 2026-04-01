/**
 * Threshold configuration editor tab.
 * Reads from and writes to /api/v1/config/thresholds.
 */

import { useCallback, useEffect, useState } from 'react'
import { api } from '@/utils/api'

interface ThresholdConfig {
  absoluteAmount: number
  percentage: number
  nettingTolerance: number
  trendConsecutiveMonths: number
}

const DEFAULT_CONFIG: ThresholdConfig = {
  absoluteAmount: 50000,
  percentage: 0.05,
  nettingTolerance: 0.10,
  trendConsecutiveMonths: 3,
}

export function AdminThresholdsTab() {
  const [config, setConfig] = useState<ThresholdConfig>(DEFAULT_CONFIG)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    api.gateway.get<ThresholdConfig>('/config/thresholds')
      .then(setConfig)
      .catch(() => {})
  }, [])

  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      await api.gateway.put('/config/thresholds', {
        absolute_amount: config.absoluteAmount,
        percentage: config.percentage,
        netting_tolerance: config.nettingTolerance,
        trend_consecutive_months: config.trendConsecutiveMonths,
      })
      setToast('Thresholds saved successfully')
      setTimeout(() => setToast(null), 3000)
    } catch {
      setToast('Failed to save thresholds')
      setTimeout(() => setToast(null), 3000)
    } finally {
      setSaving(false)
    }
  }, [config])

  const Field = ({ label, value, onChange, suffix }: {
    label: string; value: number; onChange: (v: number) => void; suffix?: string
  }) => (
    <div>
      <label className="block text-[9px] text-text-secondary mb-1 uppercase tracking-wider">{label}</label>
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
          className="w-full px-2 py-1.5 rounded-md bg-surface border border-border text-text text-[12px] font-display focus:outline-none focus:ring-1 focus:ring-accent/50"
        />
        {suffix && <span className="text-[10px] text-text-secondary">{suffix}</span>}
      </div>
    </div>
  )

  return (
    <div className="glass-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="section-label">MATERIALITY THRESHOLDS</span>
        {toast && (
          <span className={`text-[10px] px-2 py-1 rounded ${toast.includes('success') ? 'bg-emerald/10 text-emerald' : 'bg-coral/10 text-coral'}`}>
            {toast}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field
          label="Absolute threshold ($)"
          value={config.absoluteAmount}
          onChange={(v) => setConfig({ ...config, absoluteAmount: v })}
          suffix="$"
        />
        <Field
          label="Percentage threshold"
          value={config.percentage}
          onChange={(v) => setConfig({ ...config, percentage: v })}
          suffix="%"
        />
        <Field
          label="Netting tolerance"
          value={config.nettingTolerance}
          onChange={(v) => setConfig({ ...config, nettingTolerance: v })}
          suffix="%"
        />
        <Field
          label="Trend consecutive months"
          value={config.trendConsecutiveMonths}
          onChange={(v) => setConfig({ ...config, trendConsecutiveMonths: v })}
        />
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-1.5 rounded-lg text-[11px] font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, var(--cobalt), var(--accent))' }}
        >
          {saving ? 'Saving...' : 'Save Thresholds'}
        </button>
      </div>
    </div>
  )
}
