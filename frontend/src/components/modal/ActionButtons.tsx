import { useUser } from '@/context/UserContext'
import { useModal } from '@/context/ModalContext'
import { fireConfetti } from '@/components/common/ConfettiContainer'
import type { VarianceDetail } from '@/context/ModalContext'

interface ActionButtonsProps {
  data: VarianceDetail
}

export function ActionButtons({ data }: ActionButtonsProps) {
  const { persona } = useUser()
  const { updateVariance, closeModal } = useModal()

  const handleAction = (
    newStatus: VarianceDetail['status'],
    withConfetti = false,
  ) => {
    if (withConfetti) fireConfetti()
    updateVariance({ status: newStatus })
    closeModal()
  }

  // Already terminal states
  if (data.status === 'approved') {
    return (
      <div>
        <span className="section-label">ACTIONS</span>
        <div className="mt-1.5">
          <span
            className="text-[11px] font-semibold px-3 py-1.5 rounded-button inline-block"
            style={{
              background: 'var(--emerald-surface)',
              color: 'var(--emerald)',
            }}
          >
            &#10003; Approved
          </span>
        </div>
      </div>
    )
  }

  if (data.status === 'autoclosed') {
    return (
      <div>
        <span className="section-label">ACTIONS</span>
        <div className="mt-1.5">
          <span
            className="text-[11px] font-semibold px-3 py-1.5 rounded-button inline-block"
            style={{
              background: 'var(--purple-surface)',
              color: 'var(--purple)',
            }}
          >
            &#8635; Auto-closed
          </span>
        </div>
      </div>
    )
  }

  // Draft + analyst or director: Confirm, Escalate, Dismiss
  if (data.status === 'draft' && (persona === 'analyst' || persona === 'director')) {
    return (
      <div>
        <span className="section-label">ACTIONS</span>
        <div className="flex gap-1.5 mt-1.5">
          <button
            onClick={() => handleAction('reviewed', true)}
            className="text-[10px] font-semibold px-3 py-1.5 rounded-button text-white"
            style={{ background: 'linear-gradient(135deg, #002C77, #00A8C7)' }}
          >
            Confirm &amp; Review
          </button>
          <button
            onClick={() => handleAction('reviewed')}
            className="text-[10px] font-semibold px-3 py-1.5 rounded-button"
            style={{
              background: 'var(--amber-surface)',
              color: 'var(--amber)',
              border: '1px solid rgba(251,191,36,.2)',
            }}
          >
            Escalate
          </button>
          <button
            onClick={() => handleAction('autoclosed')}
            className="text-[10px] font-semibold px-3 py-1.5 rounded-button text-tx-tertiary"
            style={{ border: '1px solid var(--border)' }}
          >
            Dismiss
          </button>
        </div>
      </div>
    )
  }

  // Reviewed + director: Approve, Hold
  if (data.status === 'reviewed' && persona === 'director') {
    return (
      <div>
        <span className="section-label">ACTIONS</span>
        <div className="flex gap-1.5 mt-1.5">
          <button
            onClick={() => handleAction('approved', true)}
            className="text-[10px] font-semibold px-3 py-1.5 rounded-button text-white"
            style={{ background: 'linear-gradient(135deg, #002C77, #00A8C7)' }}
          >
            Approve
          </button>
          <button
            onClick={() => handleAction('reviewed')}
            className="text-[10px] font-semibold px-3 py-1.5 rounded-button text-tx-tertiary"
            style={{ border: '1px solid var(--border)' }}
          >
            Hold
          </button>
        </div>
      </div>
    )
  }

  // Default: read-only status display
  return (
    <div>
      <span className="section-label">ACTIONS</span>
      <div className="mt-1.5 text-[10px] text-tx-tertiary">
        No actions available for your role on this item.
      </div>
    </div>
  )
}
