import { useEffect } from 'react'
import { useModal } from '@/context/ModalContext'
import { api } from '@/utils/api'
import { transformDecompositionComponents } from '@/utils/transformers'
import { ModalHeader } from './ModalHeader'
import { BigNumberCard } from './BigNumberCard'
import { DecompositionSection } from './DecompositionSection'
import { CorrelationCards } from './CorrelationCards'
import { NarrativeSection } from './NarrativeSection'
import { HypothesisCards } from './HypothesisCards'
import { PeriodTrend } from './PeriodTrend'
import { ActionButtons } from './ActionButtons'

export function VarianceModal() {
  const { isOpen, varianceData, closeModal, updateVariance } = useModal()

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeModal()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleEsc)
    }
    return () => document.removeEventListener('keydown', handleEsc)
  }, [isOpen, closeModal])

  // Fetch decomposition from API when modal opens
  useEffect(() => {
    if (!isOpen || !varianceData?.id) return
    api.computation.get(`/drilldown/decomposition/${varianceData.id}`)
      .then((resp: any) => {
        if (resp?.components) {
          const transformed = transformDecompositionComponents(resp.components)
          if (transformed.length > 0) {
            updateVariance({ decomposition: transformed })
          }
        }
      })
      .catch(() => {}) // Keep existing decomposition data
  }, [isOpen, varianceData?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!isOpen || !varianceData) return null

  return (
    <div
      className="fixed inset-0 z-[500] flex justify-end"
      style={{
        background: 'rgba(0,0,0,.5)',
        backdropFilter: 'blur(6px)',
        animation: 'modal-fade-in 0.2s ease forwards',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) closeModal()
      }}
    >
      <style>{`
        @keyframes modal-fade-in { from { opacity: 0; } to { opacity: 1; } }
        @keyframes modal-slide-in { from { transform: translateX(100%); } to { transform: translateX(0); } }
      `}</style>
      <div
        className="w-[500px] max-w-[92vw] h-screen overflow-y-auto"
        style={{
          background: 'var(--surface)',
          borderLeft: '1px solid var(--glass-border)',
          boxShadow: '-8px 0 32px rgba(0,0,0,.2)',
          animation: 'modal-slide-in 0.25s cubic-bezier(.22,1,.36,1) forwards',
        }}
      >
        <ModalHeader data={varianceData} onClose={closeModal} />
        <div className="p-4 space-y-3">
          <BigNumberCard data={varianceData} />
          <DecompositionSection data={varianceData.decomposition} />
          {varianceData.correlations.length > 0 && (
            <CorrelationCards data={varianceData.correlations} />
          )}
          <NarrativeSection data={varianceData} />
          <HypothesisCards data={varianceData} />
          <PeriodTrend data={varianceData} />
          <ActionButtons data={varianceData} />
        </div>
      </div>
    </div>
  )
}
