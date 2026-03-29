import { Badge } from '@/components/common/Badge'
import type { VarianceDetail } from '@/context/ModalContext'

interface ModalHeaderProps {
  data: VarianceDetail
  onClose: () => void
}

const typeBadge: Record<string, { variant: 'coral' | 'purple' | 'amber'; label: string }> = {
  material: { variant: 'coral', label: 'Material' },
  netted: { variant: 'purple', label: 'Netted' },
  trending: { variant: 'amber', label: 'Trending' },
}

const statusBadge: Record<string, { variant: 'emerald' | 'gold' | 'gray' | 'purple'; label: string }> = {
  approved: { variant: 'emerald', label: 'Approved' },
  reviewed: { variant: 'gold', label: 'Reviewed' },
  draft: { variant: 'gray', label: 'AI Draft' },
  autoclosed: { variant: 'purple', label: 'Auto-closed' },
}

export function ModalHeader({ data, onClose }: ModalHeaderProps) {
  const tConf = typeBadge[data.type]
  const sConf = statusBadge[data.status]

  return (
    <div
      className="sticky top-0 z-10 px-4 py-3 border-b border-border"
      style={{ background: 'var(--surface)' }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* Pills row */}
          <div className="flex items-center gap-1.5 mb-1.5">
            <Badge variant={tConf.variant}>{tConf.label}</Badge>
            <Badge variant={sConf.variant}>{sConf.label}</Badge>
            {data.isEdited && <Badge variant="teal">edited</Badge>}
            {data.isNew && <Badge variant="amber">New</Badge>}
            {data.noBudget && <Badge variant="coral">No budget</Badge>}
            {data.noPriorYear && <Badge variant="gray">No PY</Badge>}
            {data.isSynthesized && (
              <Badge variant="purple">
                synth{data.synthCount ? ` (${data.synthCount})` : ''}
              </Badge>
            )}
          </div>

          {/* Account name */}
          <h2
            className="text-[14px] font-bold text-tx-primary truncate"
            style={{ fontFamily: "'Playfair Display', Georgia, serif" }}
          >
            {data.account}
          </h2>

          {/* Metadata line */}
          <div className="text-[10px] text-tx-tertiary mt-0.5">
            {data.bu} &middot; {data.geo} &middot;{' '}
            {data.favorable ? 'Favorable' : 'Unfavorable'}
          </div>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="flex items-center justify-center w-6 h-6 rounded text-tx-tertiary text-sm hover:text-white transition-colors"
          style={{ background: 'transparent' }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--coral, #F97066)'
            e.currentTarget.style.color = '#fff'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent'
            e.currentTarget.style.color = ''
          }}
          aria-label="Close modal"
        >
          &times;
        </button>
      </div>
    </div>
  )
}
