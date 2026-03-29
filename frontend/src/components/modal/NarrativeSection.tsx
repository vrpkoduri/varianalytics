import { useState } from 'react'
import { useModal } from '@/context/ModalContext'
import { useUser } from '@/context/UserContext'
import { Badge } from '@/components/common/Badge'
import type { VarianceDetail } from '@/context/ModalContext'

interface NarrativeSectionProps {
  data: VarianceDetail
}

const personaNarrativeLevel: Record<string, keyof VarianceDetail['narratives']> = {
  analyst: 'detail',
  director: 'midlevel',
  cfo: 'summary',
  bu: 'midlevel',
}

export function NarrativeSection({ data }: NarrativeSectionProps) {
  const { updateVariance } = useModal()
  const { persona } = useUser()

  const level = personaNarrativeLevel[persona] ?? 'detail'
  const currentNarrative = data.editedNarrative ?? data.narratives[level]

  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState(currentNarrative)
  const [showCFOPreview, setShowCFOPreview] = useState(false)
  const [showReasoning, setShowReasoning] = useState(false)

  const handleSave = () => {
    updateVariance({ editedNarrative: editText, isEdited: true, editedBy: persona })
    setIsEditing(false)
  }

  const handleCancel = () => {
    setEditText(currentNarrative)
    setIsEditing(false)
  }

  return (
    <div>
      <span className="section-label">NARRATIVE</span>

      <div className="mt-1.5">
        {/* Level badge */}
        <div className="flex items-center gap-1.5 mb-1.5">
          <Badge variant="teal">{level}</Badge>
          {data.isEdited && (
            <span className="text-[9px] text-tx-tertiary">(edited by {data.editedBy})</span>
          )}
        </div>

        {/* Display / Edit mode */}
        {isEditing ? (
          <div>
            <textarea
              className="w-full p-2.5 rounded-lg text-[11px] leading-relaxed text-tx-primary resize-y min-h-[80px]"
              style={{
                background: 'var(--surface)',
                border: '2px solid #00A8C7',
                outline: 'none',
              }}
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              autoFocus
            />
            <div className="flex gap-1.5 mt-1.5">
              <button
                onClick={handleSave}
                className="text-[9px] font-semibold px-3 py-1 rounded-button text-white"
                style={{ background: 'linear-gradient(135deg, #002C77, #00A8C7)' }}
              >
                Save
              </button>
              <button
                onClick={handleCancel}
                className="text-[9px] font-semibold px-3 py-1 rounded-button text-tx-tertiary"
                style={{ border: '1px solid var(--border)' }}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div
            className="p-2.5 rounded-lg text-[11px] leading-relaxed text-tx-secondary"
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
            }}
          >
            {currentNarrative}
          </div>
        )}

        {/* Original AI text when edited */}
        {data.isEdited && !isEditing && (
          <div className="mt-1 text-[9px] text-tx-tertiary italic">
            Original AI: {data.narratives[level]}
          </div>
        )}

        {/* CFO Preview */}
        {showCFOPreview && (
          <div
            className="mt-1.5 p-2.5 rounded-lg text-[11px] leading-relaxed"
            style={{
              background: 'var(--amber-surface)',
              border: '1px solid rgba(251,191,36,.15)',
            }}
          >
            <span className="text-[8px] font-bold text-amber uppercase tracking-wide">
              CFO Preview
            </span>
            <div className="text-tx-secondary mt-1">{data.narratives.summary}</div>
          </div>
        )}

        {/* Reasoning */}
        {showReasoning && (
          <div
            className="mt-1.5 p-2.5 rounded-lg text-[11px] leading-relaxed"
            style={{
              background: 'var(--purple-surface)',
              border: '1px solid rgba(167,139,250,.15)',
            }}
          >
            <span className="text-[8px] font-bold text-purple uppercase tracking-wide">
              AI Reasoning
            </span>
            <div className="text-tx-secondary mt-1">
              Narrative generated from {data.decomposition.length}-factor decomposition
              with {data.correlations.length} correlated variance(s).
              {data.isSynthesized && ` Synthesized from ${data.synthCount ?? 0} child commentaries.`}
              {data.projectedYE && ` YE projection: ${data.projectedYE.confidence} confidence.`}
            </div>
          </div>
        )}

        {/* Button bar */}
        {!isEditing && (
          <div className="flex gap-1.5 mt-2">
            <button
              onClick={() => {
                setEditText(currentNarrative)
                setIsEditing(true)
              }}
              className="text-[9px] font-medium px-2.5 py-1 rounded-button text-tx-secondary hover:text-teal transition-colors"
              style={{ border: '1px solid var(--border)' }}
            >
              Edit
            </button>
            <button
              onClick={() => setShowCFOPreview(!showCFOPreview)}
              className="text-[9px] font-medium px-2.5 py-1 rounded-button text-tx-secondary hover:text-teal transition-colors"
              style={{ border: '1px solid var(--border)' }}
            >
              {showCFOPreview ? 'Hide' : 'Preview as'} CFO
            </button>
            <button
              onClick={() => setShowReasoning(!showReasoning)}
              className="text-[9px] font-medium px-2.5 py-1 rounded-button text-tx-secondary hover:text-teal transition-colors"
              style={{ border: '1px solid var(--border)' }}
            >
              {showReasoning ? 'Hide' : 'Show'} Reasoning
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
