import { SectionLabel } from '@/components/common/SectionLabel'
import { fireConfetti } from '@/components/common/ConfettiContainer'
import { cn } from '@/utils/theme'
import type { ReviewVariance } from '@/mocks/reviewData'

interface ReviewItemExpandedProps {
  item: ReviewVariance
  onOpenModal: () => void
  onConfirm: () => void
  onHypothesisFeedback: (hyIndex: number, feedback: -1 | 0 | 1) => void
}

const confidenceDotColor: Record<string, string> = {
  High: 'bg-emerald',
  Medium: 'bg-amber',
  Low: 'bg-coral',
}

export function ReviewItemExpanded({ item, onOpenModal, onConfirm, onHypothesisFeedback }: ReviewItemExpandedProps) {
  const maxDecomp = Math.max(...item.decomposition.map((d) => Math.abs(d.value)), 1)

  return (
    <div className="pl-11 pr-3 pb-3 animate-expand-in">
      {/* NARRATIVE */}
      <SectionLabel className="mt-2">Narrative</SectionLabel>
      <div
        className={cn(
          'text-[11px] leading-[1.8] text-[var(--tx-primary)]',
          'bg-[var(--card)] border border-border rounded-lg px-3 py-2 mb-3',
        )}
      >
        {item.narratives.detail}
      </div>

      {/* DECOMPOSITION */}
      <SectionLabel>Decomposition</SectionLabel>
      <div className="flex flex-wrap gap-2 mb-3">
        {item.decomposition.map((d, i) => (
          <div
            key={d.label}
            className="bg-[var(--card)] border border-border rounded-lg px-2.5 py-1.5 min-w-[90px]"
          >
            <div className="text-[8px] text-tx-tertiary mb-0.5">{d.label}</div>
            <div
              className={cn(
                'text-[11px] font-bold',
                d.value >= 0 ? 'text-emerald' : 'text-coral',
              )}
            >
              {d.value >= 0 ? '+' : ''}${Math.abs(d.value).toLocaleString()}
              <span className="text-[8px] text-tx-tertiary ml-1">({d.pct}%)</span>
            </div>
            <div className="h-[3px] rounded-full bg-border mt-1 overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full animate-bar-slide',
                  d.value >= 0 ? 'bg-emerald' : 'bg-coral',
                )}
                style={{
                  '--bar-w': `${(Math.abs(d.value) / maxDecomp) * 100}%`,
                  animationDelay: `${i * 100}ms`,
                } as React.CSSProperties}
              />
            </div>
          </div>
        ))}
      </div>

      {/* HYPOTHESES */}
      <SectionLabel>Hypotheses</SectionLabel>
      <div className="space-y-1.5 mb-3">
        {item.hypotheses.map((h, i) => (
          <div
            key={i}
            className="flex items-start gap-2 bg-[var(--card)] border border-border rounded-lg px-2.5 py-1.5"
          >
            <div
              className={cn(
                'w-[6px] h-[6px] rounded-full shrink-0 mt-1',
                confidenceDotColor[h.confidence],
              )}
            />
            <div className="flex-1 min-w-0">
              <div className="text-[10px] text-[var(--tx-primary)] leading-relaxed">{h.text}</div>
              <div className="text-[8px] text-tx-tertiary mt-0.5">{h.confidence} confidence</div>
            </div>
            <div className="shrink-0 flex items-center gap-1">
              {h.feedback === 0 ? (
                <>
                  <button
                    type="button"
                    className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-surface text-emerald hover:bg-emerald/20 transition-colors"
                    onClick={(e) => { e.stopPropagation(); onHypothesisFeedback(i, 1) }}
                    aria-label="Confirm hypothesis"
                  >
                    {'\u2713'}
                  </button>
                  <button
                    type="button"
                    className="text-[10px] px-1.5 py-0.5 rounded bg-coral-surface text-coral hover:bg-coral/20 transition-colors"
                    onClick={(e) => { e.stopPropagation(); onHypothesisFeedback(i, -1) }}
                    aria-label="Reject hypothesis"
                  >
                    {'\u2717'}
                  </button>
                </>
              ) : h.feedback === 1 ? (
                <span className="text-[9px] text-emerald font-medium">{'\u2713'} Confirmed</span>
              ) : (
                <span className="text-[9px] text-coral font-medium">{'\u2717'} Rejected</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* ACTION BAR */}
      <div className="flex items-center gap-2 pt-1 border-t border-border">
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onOpenModal() }}
          className={cn(
            'text-[9px] font-semibold px-2.5 py-1 rounded-button',
            'border border-border text-tx-secondary',
            'hover:border-teal hover:text-teal transition-all duration-150',
          )}
        >
          Detail {'\u2192'}
        </button>
        {item.status === 'draft' && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              fireConfetti()
              onConfirm()
            }}
            className={cn(
              'text-[9px] font-semibold px-3 py-1 rounded-button',
              'bg-gradient-to-r from-cobalt to-teal text-white',
              'hover:shadow-button-hover transition-all duration-150',
            )}
          >
            Confirm
          </button>
        )}
      </div>
    </div>
  )
}
