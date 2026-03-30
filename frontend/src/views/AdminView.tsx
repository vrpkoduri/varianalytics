import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'

const ENGINE_STATUS = [
  { label: 'Last run', value: '18 min ago' },
  { label: 'Coverage', value: '100%' },
  { label: 'Material variances', value: '25' },
]

const THRESHOLDS = [
  { label: 'Global absolute', value: '$50K' },
  { label: 'Global percentage', value: '3%' },
  { label: 'Revenue override', value: '2%' },
  { label: 'T&E override', value: '5%' },
]

const MODELS = [
  { label: 'litellm_model', value: 'azure/gpt-4o' },
  { label: 'fast_model', value: 'azure/gpt-4o-mini' },
  { label: 'embedding_model', value: 'azure/text-embedding-3-large' },
]

const PERSONAS = [
  { role: 'Analyst', scope: 'Full detail access, all BUs, all accounts' },
  { role: 'Director', scope: 'Mid-level narratives, approval queue, all BUs' },
  { role: 'CFO', scope: 'Summary + board narratives, approved only' },
  { role: 'BU Leader', scope: 'Mid-level, scoped to own BU only' },
]

export default function AdminView() {
  return (
    <div className="space-y-3">
      <Breadcrumb title="Admin" subtitle="System configuration (read-only)" />

      {/* Engine Status */}
      <div className="glass-card p-4 animate-fade-up d0">
        <span className="section-label">ENGINE STATUS</span>
        <div className="grid grid-cols-3 gap-4 mt-3">
          {ENGINE_STATUS.map((item) => (
            <div key={item.label}>
              <div className="text-[9px] text-tx-tertiary mb-0.5">{item.label}</div>
              <div className="text-[13px] font-semibold font-display" style={{ color: 'var(--tx-primary)' }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Threshold Configuration */}
      <div className="glass-card p-4 animate-fade-up d1">
        <span className="section-label">THRESHOLD CONFIGURATION</span>
        <div className="grid grid-cols-2 tablet:grid-cols-4 gap-4 mt-3">
          {THRESHOLDS.map((item) => (
            <div key={item.label}>
              <div className="text-[9px] text-tx-tertiary mb-0.5">{item.label}</div>
              <div className="text-[13px] font-semibold font-display" style={{ color: 'var(--teal)' }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Model Routing */}
      <div className="glass-card p-4 animate-fade-up d2">
        <span className="section-label">MODEL ROUTING</span>
        <div className="space-y-2 mt-3">
          {MODELS.map((item) => (
            <div key={item.label} className="flex items-center justify-between text-[10px]">
              <span className="text-tx-tertiary font-mono">{item.label}</span>
              <span className="text-tx-secondary font-medium">{item.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Persona Configuration */}
      <div className="glass-card p-4 animate-fade-up d3">
        <span className="section-label">PERSONA CONFIGURATION</span>
        <div className="space-y-2 mt-3">
          {PERSONAS.map((item) => (
            <div key={item.role} className="flex items-center justify-between text-[10px]">
              <span className="text-tx-primary font-semibold">{item.role}</span>
              <span className="text-tx-secondary">{item.scope}</span>
            </div>
          ))}
        </div>
      </div>

      <MarshFooter />
    </div>
  )
}
