import { LoadingSkeleton } from '@/components/common/LoadingSkeleton'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { MarshFooter } from '@/components/common/MarshFooter'
import { SegmentedProgressBar } from '@/components/review/SegmentedProgressBar'
import { StatusCounterCards } from '@/components/review/StatusCounterCards'
import { BatchActionBar } from '@/components/review/BatchActionBar'
import { ReviewSortBar } from '@/components/review/ReviewSortBar'
import { ReviewList } from '@/components/review/ReviewList'
import { useReviewQueue } from '@/hooks/useReviewQueue'
import { useUser } from '@/context/UserContext'
import { useModal } from '@/context/ModalContext'
import { MOCK_MODAL_DATA } from '@/mocks/modalData'
import type { ReviewVariance } from '@/mocks/reviewData'
import type { VarianceDetail } from '@/context/ModalContext'

export default function ReviewView() {
  const { persona } = useUser()
  const { openModal } = useModal()

  const {
    items,
    counts,
    statusFilter,
    setStatusFilter,
    sortBy,
    cycleSortBy,
    searchQuery,
    setSearchQuery,
    expandedIds,
    toggleExpand,
    checkedIds,
    toggleCheck,
    batchMarkReviewed,
    updateItemStatus,
    updateHypothesisFeedback,
    loading,
    usingMock,
  } = useReviewQueue(persona)

  const handleOpenModal = (item: ReviewVariance) => {
    // If item maps to MOCK_MODAL_DATA, use that for full detail; otherwise build from review data
    if (item.varianceId && MOCK_MODAL_DATA[item.varianceId]) {
      openModal(MOCK_MODAL_DATA[item.varianceId])
    } else {
      const detail: VarianceDetail = {
        id: item.id,
        account: item.account,
        bu: item.bu,
        geo: item.geo,
        variance: item.variance,
        variancePct: item.variancePct,
        favorable: item.favorable,
        type: item.type,
        status: item.status,
        sparkData: item.sparkData,
        decomposition: item.decomposition,
        correlations: [],
        hypotheses: item.hypotheses,
        narratives: item.narratives,
        isEdited: item.isEdited,
        editedBy: item.editedBy,
        isSynthesized: item.isSynthesized,
        synthCount: item.synthCount,
        isNew: item.edgeBadge === 'New',
        noBudget: item.edgeBadge === 'No budget',
        noPriorYear: false,
        edgeBadge: item.edgeBadge,
        narrative: item.narratives.detail,
      }
      openModal(detail)
    }
  }

  const handleConfirm = (id: string) => {
    updateItemStatus(id, 'reviewed')
  }

  if (loading) {
    return (
      <div className="space-y-4 px-6 py-5 max-w-[1300px] mx-auto">
        <LoadingSkeleton height="30px" width="200px" />
        <LoadingSkeleton height="32px" />
        <div className="grid grid-cols-4 gap-2.5">
          {Array.from({ length: 4 }).map((_, i) => (
            <LoadingSkeleton key={i} height="80px" />
          ))}
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <LoadingSkeleton key={i} height="130px" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4 px-6 py-5 max-w-[1300px] mx-auto">
      <Breadcrumb title="Review Queue" subtitle="Analyst Workspace" />

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

      {/* BU Leader scope banner */}
      {persona === 'bu' && (
        <div className="text-[9px] text-amber bg-amber-surface px-3 py-1.5 rounded-lg border border-amber/20 animate-fade-up">
          Showing Marsh variances only (BU Leader scope)
        </div>
      )}

      <SegmentedProgressBar
        approved={counts.approved}
        reviewed={counts.reviewed}
        draft={counts.awaiting}
      />

      <StatusCounterCards
        counts={counts}
        activeFilter={statusFilter}
        onFilterChange={setStatusFilter}
      />

      <BatchActionBar
        selectedCount={checkedIds.size}
        onBatchAction={batchMarkReviewed}
      />

      <ReviewSortBar
        sortBy={sortBy}
        searchQuery={searchQuery}
        onSortChange={cycleSortBy}
        onSearchChange={setSearchQuery}
      />

      <ReviewList
        items={items}
        expandedIds={expandedIds}
        checkedIds={checkedIds}
        onToggleExpand={toggleExpand}
        onToggleCheck={toggleCheck}
        onOpenModal={handleOpenModal}
        onConfirm={handleConfirm}
        onHypothesisFeedback={updateHypothesisFeedback}
      />

      <MarshFooter />
    </div>
  )
}
