import { Badge } from '@/components/common/Badge'
import { InfoTooltip } from '@/components/common/Tooltip'
import { TOOLTIPS } from '@/mocks/tooltipContent'
import { personas } from '@/theme/tokens'

interface ExecSummaryProps {
  narrative: string
  persona: string
}

export function ExecSummary({ narrative, persona }: ExecSummaryProps) {
  const personaConfig = personas[persona as keyof typeof personas]
  const label = personaConfig?.label ?? persona

  return (
    <div className="glass-card p-4 border-l-2 border-l-teal animate-fade-up d2">
      <div className="flex items-center gap-2 mb-2">
        <span className="section-label">EXECUTIVE SUMMARY</span>
        <InfoTooltip content={TOOLTIPS.execSummary} />
        <Badge variant="teal">{label}</Badge>
      </div>
      <div
        className="text-body-md text-tx-secondary leading-relaxed"
        dangerouslySetInnerHTML={{ __html: narrative }}
      />
    </div>
  )
}
