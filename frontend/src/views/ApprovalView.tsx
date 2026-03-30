import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'
import { ReportGate } from '@/components/approval/ReportGate'
import { AnalystGroup } from '@/components/approval/AnalystGroup'
import { useApprovalQueue } from '@/hooks/useApprovalQueue'
import { useModal } from '@/context/ModalContext'
import { MOCK_MODAL_DATA } from '@/mocks/modalData'
import type { ApprovalVariance } from '@/mocks/approvalData'

export default function ApprovalView() {
  const { analystGroups, pendingCount, approveItem, holdItem, approveAllReviewed, bulkApproveGroup } = useApprovalQueue()
  const { openModal } = useModal()

  const handleOpenModal = (item: ApprovalVariance) => {
    const modalData = MOCK_MODAL_DATA[item.varianceId || '']
    if (modalData) openModal(modalData)
  }

  return (
    <div className="space-y-3">
      <Breadcrumb title="Approvals" subtitle="Director approval queue" />
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
