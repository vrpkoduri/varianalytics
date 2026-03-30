import { useUser } from '@/context/UserContext'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'
import { ReportGate } from '@/components/approval/ReportGate'
import { AnalystGroup } from '@/components/approval/AnalystGroup'
import { useApprovalQueue } from '@/hooks/useApprovalQueue'
import { useModal } from '@/context/ModalContext'
import { MOCK_MODAL_DATA } from '@/mocks/modalData'
import type { ApprovalVariance } from '@/mocks/approvalData'

export default function ApprovalView() {
  const { persona } = useUser()
  const {
    analystGroups,
    pendingCount,
    approveItem,
    holdItem,
    approveAllReviewed,
    bulkApproveGroup,
    loading,
    usingMock,
  } = useApprovalQueue()
  const { openModal } = useModal()

  const handleOpenModal = (item: ApprovalVariance) => {
    const modalData = MOCK_MODAL_DATA[item.varianceId || '']
    if (modalData) openModal(modalData)
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <Breadcrumb title="Approvals" subtitle="Director approval queue" />
        <div className="glass-card p-4 h-24 animate-pulse" style={{ background: 'var(--glass)' }} />
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="glass-card p-4 h-40 animate-pulse"
            style={{ background: 'var(--glass)' }}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <Breadcrumb title="Approvals" subtitle="Director approval queue" />

      {usingMock && (
        <div
          className="px-3 py-1 rounded text-[9px] text-tx-secondary"
          style={{
            background: 'rgba(255,191,0,.06)',
            border: '1px solid rgba(255,191,0,.15)',
          }}
        >
          Using cached data — backend unavailable
        </div>
      )}

      {persona === 'bu' && (
        <div
          className="px-3 py-1.5 rounded-lg text-[9px] animate-fade-up"
          style={{
            background: 'rgba(0,168,199,.06)',
            border: '1px solid rgba(0,168,199,.12)',
          }}
        >
          <span className="font-semibold" style={{ color: 'var(--teal)' }}>&#128274; Marsh</span>
          <span className="ml-1" style={{ color: 'var(--tx-secondary)' }}>Showing data scoped to your business unit</span>
        </div>
      )}
      <ReportGate pendingCount={pendingCount} onApproveAllReviewed={approveAllReviewed} />
      {analystGroups.map((group) => (
        <AnalystGroup
          key={group.name}
          group={group}
          onApproveItem={approveItem}
          onHoldItem={holdItem}
          onBulkApprove={() => bulkApproveGroup(group.name)}
          onOpenModal={handleOpenModal}
        />
      ))}
      <MarshFooter />
    </div>
  )
}
