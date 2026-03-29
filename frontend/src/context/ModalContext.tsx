import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from 'react'

// ---------- Types ----------

export interface VarianceDetail {
  id: string
  account: string
  bu: string
  geo: string
  variance: number
  variancePct: number
  favorable: boolean
  type: 'material' | 'netted' | 'trending'
  status: 'approved' | 'reviewed' | 'draft' | 'autoclosed'
  sparkData: number[]
  decomposition: Array<{ label: string; value: number; pct: number }>
  correlations: Array<{
    account: string
    pct: number
    favorable: boolean
    hypothesis: string
    confidence: number
  }>
  hypotheses: Array<{
    text: string
    confidence: 'High' | 'Medium' | 'Low'
    feedback: -1 | 0 | 1
  }>
  narratives: {
    detail: string
    midlevel: string
    summary: string
    board: string
  }
  editedNarrative?: string
  editedBy?: string
  isEdited: boolean
  isSynthesized: boolean
  synthCount?: number
  projectedYE?: { amount: number; confidence: string }
  isNew: boolean
  noBudget: boolean
  noPriorYear: boolean
  edgeBadge?: string
  narrative: string
}

interface ModalContextValue {
  isOpen: boolean
  varianceData: VarianceDetail | null
  openModal: (v: VarianceDetail) => void
  closeModal: () => void
  updateVariance: (updates: Partial<VarianceDetail>) => void
}

// ---------- Context ----------

const ModalContext = createContext<ModalContextValue | undefined>(undefined)

export function ModalProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const [varianceData, setVarianceData] = useState<VarianceDetail | null>(null)

  const openModal = useCallback((v: VarianceDetail) => {
    setVarianceData(v)
    setIsOpen(true)
  }, [])

  const closeModal = useCallback(() => {
    setIsOpen(false)
    // Allow slide-out animation before clearing data
    setTimeout(() => setVarianceData(null), 300)
  }, [])

  const updateVariance = useCallback((updates: Partial<VarianceDetail>) => {
    setVarianceData((prev) => (prev ? { ...prev, ...updates } : prev))
  }, [])

  return (
    <ModalContext.Provider
      value={{ isOpen, varianceData, openModal, closeModal, updateVariance }}
    >
      {children}
    </ModalContext.Provider>
  )
}

export function useModal(): ModalContextValue {
  const context = useContext(ModalContext)
  if (!context) {
    throw new Error('useModal must be used within a ModalProvider')
  }
  return context
}
