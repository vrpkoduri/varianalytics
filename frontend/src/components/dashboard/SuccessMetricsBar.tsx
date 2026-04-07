import type { MockMetrics } from '@/mocks/dashboardData'

interface SuccessMetricsBarProps {
  metrics: MockMetrics
}

const metricDefs = [
  { key: 'cycleTime' as const, label: 'CYCLE TIME', suffix: 'min', icon: '\u23F1' },
  { key: 'coverage' as const, label: 'COVERAGE', suffix: '%', icon: '\u2713' },
  { key: 'rootCause' as const, label: 'ROOT CAUSE', suffix: '%', icon: '\u26A1' },
  { key: 'commentary' as const, label: 'COMMENTARY', suffix: '%', icon: '\u270E' },
]

export function SuccessMetricsBar({ metrics }: SuccessMetricsBarProps) {
  return (
    <div className="glass-card px-4 py-2 flex items-center gap-4 animate-fade-up d1 overflow-x-auto">
      <span className="section-label flex-shrink-0">SUCCESS METRICS</span>
      <div className="flex items-center gap-4 flex-wrap">
        {metricDefs.map((def) => (
          <div key={def.key} className="flex items-center gap-1.5 text-[10px]">
            <span className="text-teal text-xs">{def.icon}</span>
            <span className="text-tx-tertiary">{def.label}</span>
            <span className="text-tx-primary font-semibold">
              {metrics[def.key]}{def.suffix}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
