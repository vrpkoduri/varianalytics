import { useModal } from '@/context/ModalContext'
import type { VarianceDetail } from '@/context/ModalContext'

interface HypothesisCardsProps {
  data: VarianceDetail
}

const confidenceDot: Record<string, string> = {
  High: 'var(--emerald)',
  Medium: 'var(--amber)',
  Low: 'var(--coral)',
}

export function HypothesisCards({ data }: HypothesisCardsProps) {
  const { updateVariance } = useModal()

  if (data.hypotheses.length === 0) return null

  const handleFeedback = (index: number, feedback: -1 | 1) => {
    const updated = data.hypotheses.map((h, i) =>
      i === index ? { ...h, feedback } : h,
    )
    updateVariance({ hypotheses: updated })
  }

  return (
    <div>
      <span className="section-label">HYPOTHESES</span>
      <div className="space-y-1.5 mt-1.5">
        {data.hypotheses.map((h, idx) => (
          <div
            key={idx}
            className="p-2.5 rounded-lg"
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
            }}
          >
            <div className="flex items-start gap-2">
              {/* Confidence dot */}
              <span
                className="w-2 h-2 rounded-full flex-shrink-0 mt-0.5"
                style={{ background: confidenceDot[h.confidence] }}
              />

              <div className="flex-1 min-w-0">
                {/* Hypothesis text */}
                <div className="text-[10px] text-tx-secondary leading-snug">
                  {h.text}
                </div>

                {/* Confidence label + feedback */}
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className="text-[9px] font-semibold"
                    style={{ color: confidenceDot[h.confidence] }}
                  >
                    {h.confidence}
                  </span>

                  {h.feedback === 0 && (
                    <div className="flex gap-1 ml-auto">
                      <button
                        onClick={() => handleFeedback(idx, 1)}
                        className="text-[10px] px-1.5 py-0.5 rounded hover:bg-emerald-surface transition-colors"
                        style={{ color: 'var(--emerald)' }}
                        aria-label="Confirm hypothesis"
                      >
                        &#10003;
                      </button>
                      <button
                        onClick={() => handleFeedback(idx, -1)}
                        className="text-[10px] px-1.5 py-0.5 rounded hover:bg-coral-surface transition-colors"
                        style={{ color: 'var(--coral)' }}
                        aria-label="Reject hypothesis"
                      >
                        &#10007;
                      </button>
                    </div>
                  )}

                  {h.feedback === 1 && (
                    <span className="text-[9px] ml-auto" style={{ color: 'var(--emerald)' }}>
                      &#10003; Confirmed
                    </span>
                  )}

                  {h.feedback === -1 && (
                    <span className="text-[9px] ml-auto" style={{ color: 'var(--coral)' }}>
                      &#10007; Rejected
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
