import { GlassCard } from '@/components/common/GlassCard'
import { Badge } from '@/components/common/Badge'
import type { TemplateItem } from '@/mocks/reportsData'

interface TemplateCardProps {
  template: TemplateItem
  onGenerate: () => void
}

export function TemplateCard({ template, onGenerate }: TemplateCardProps) {
  return (
    <GlassCard className="flex items-center justify-between p-3 px-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold truncate">{template.name}</span>
          <Badge variant="teal">{template.type}</Badge>
        </div>
        <div className="text-[9px] text-tx-tertiary mt-1">{template.description}</div>
      </div>
      <div className="flex items-center gap-1.5 shrink-0 ml-3">
        <button
          onClick={onGenerate}
          className="px-3 py-1 rounded-button text-[8px] font-semibold bg-gradient-to-r from-cobalt to-teal text-white shadow-[0_2px_8px_rgba(0,168,199,.2)] hover:shadow-[0_6px_20px_rgba(0,168,199,.3)] transition-shadow"
        >
          Generate
        </button>
        <button
          className="px-2.5 py-1 rounded-button text-[8px] font-semibold border border-border/50 text-tx-tertiary opacity-50 cursor-not-allowed"
          disabled
        >
          Customize
        </button>
      </div>
    </GlassCard>
  )
}
