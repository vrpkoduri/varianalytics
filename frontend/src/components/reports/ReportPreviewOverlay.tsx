import { useEffect, useCallback } from 'react'
import { ReportToolbar } from './ReportToolbar'
import { ExecutiveFlashReport } from './templates/ExecutiveFlashReport'
import { PeriodEndReport } from './templates/PeriodEndReport'
import { BoardNarrativeReport } from './templates/BoardNarrativeReport'

interface ReportPreviewOverlayProps {
  reportType: 'flash' | 'period' | 'board' | null
  onClose: () => void
}

const TITLES: Record<string, string> = {
  flash: 'Executive Flash Report',
  period: 'Period-End Variance Analysis',
  board: 'Board Narrative',
}

export function ReportPreviewOverlay({ reportType, onClose }: ReportPreviewOverlayProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose],
  )

  useEffect(() => {
    if (!reportType) return
    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [reportType, handleKeyDown])

  if (!reportType) return null

  return (
    <div className="fixed inset-0 z-[600] flex flex-col bg-black/80 backdrop-blur-[8px]">
      <ReportToolbar title={TITLES[reportType]} onClose={onClose} />
      <div className="flex-1 overflow-y-auto py-8 px-4 flex flex-col items-center gap-6">
        {reportType === 'flash' && <ExecutiveFlashReport />}
        {reportType === 'period' && <PeriodEndReport />}
        {reportType === 'board' && <BoardNarrativeReport />}
      </div>
    </div>
  )
}
