/**
 * Admin panel with 5 editable tabs:
 * 1. Engine Control — run variance engine, track progress, view history (Phase 3D)
 * 2. Thresholds — edit materiality thresholds (persisted to YAML)
 * 3. Model Routing — edit LLM model configuration
 * 4. Users & Roles — CRUD user management with role assignment
 * 5. Audit Log — searchable, filterable audit trail
 */

import { useState } from 'react'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'
import { AdminEngineControlTab } from '@/components/admin/AdminEngineControlTab'
import { AdminThresholdsTab } from '@/components/admin/AdminThresholdsTab'
import { AdminModelRoutingTab } from '@/components/admin/AdminModelRoutingTab'
import { AdminUsersTab } from '@/components/admin/AdminUsersTab'
import { AdminAuditLogTab } from '@/components/admin/AdminAuditLogTab'
import { AdminLLMMonitoringTab } from '@/components/admin/AdminLLMMonitoringTab'

const TABS = [
  { key: 'engine', label: 'Engine Control' },
  { key: 'thresholds', label: 'Thresholds' },
  { key: 'models', label: 'Model Routing' },
  { key: 'llm', label: 'AI Monitoring' },
  { key: 'users', label: 'Users & Roles' },
  { key: 'audit', label: 'Audit Log' },
] as const

type TabKey = typeof TABS[number]['key']

export default function AdminView() {
  const [activeTab, setActiveTab] = useState<TabKey>('engine')

  return (
    <div className="space-y-3">
      <Breadcrumb title="Admin" subtitle="System configuration and user management" />

      {/* Tab navigation */}
      <div className="glass-card p-1 animate-fade-up d0">
        <div className="flex gap-1 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`
                flex-shrink-0 px-3 py-2 rounded-lg text-[11px] font-semibold transition-all duration-200
                ${activeTab === tab.key
                  ? 'bg-accent/20 text-accent border border-accent/30'
                  : 'text-text-secondary hover:text-text hover:bg-surface/50'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="animate-fade-up d1">
        {activeTab === 'engine' && <AdminEngineControlTab />}
        {activeTab === 'thresholds' && <AdminThresholdsTab />}
        {activeTab === 'models' && <AdminModelRoutingTab />}
        {activeTab === 'llm' && <AdminLLMMonitoringTab />}
        {activeTab === 'users' && <AdminUsersTab />}
        {activeTab === 'audit' && <AdminAuditLogTab />}
      </div>

      <MarshFooter />
    </div>
  )
}
