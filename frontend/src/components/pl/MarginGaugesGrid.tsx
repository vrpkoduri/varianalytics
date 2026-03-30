import type { MarginData } from '@/mocks/plData'
import { GlassCard } from '@/components/common/GlassCard'
import { SectionLabel } from '@/components/common/SectionLabel'
import { MarginGauge } from './MarginGauge'

interface MarginGaugesGridProps {
  margins: MarginData[]
}

export function MarginGaugesGrid({ margins }: MarginGaugesGridProps) {
  return (
    <div className="animate-fade-up">
      <SectionLabel className="mb-2">Key Margins</SectionLabel>
      <div className="grid grid-cols-5 gap-2.5 max-[1100px]:grid-cols-3 max-[700px]:grid-cols-2">
        {margins.map((m) => (
          <GlassCard key={m.id} className="p-3 flex items-center justify-center">
            <MarginGauge
              label={m.label}
              value={m.value}
              delta={m.delta}
              color={m.color}
            />
          </GlassCard>
        ))}
      </div>
    </div>
  )
}
