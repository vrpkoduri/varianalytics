import type { ChatMessage } from '@/hooks/useChat'
import type { RichContent } from '@/mocks/chatData'
import { Badge } from '@/components/common/Badge'
import { renderMarkdown } from '@/utils/markdown'
import { Sparkline } from '@/components/charts/Sparkline'
import { AgentAvatar } from './AgentAvatar'
import { StreamingCursor } from './StreamingCursor'
import { VarianceCallout } from './VarianceCallout'
import { NettingAlert } from './NettingAlert'
import { InlineDataTable } from './InlineDataTable'
import { SuggestionPills } from './SuggestionPills'

interface AgentMessageProps {
  message: ChatMessage
  isStreaming: boolean
  onSuggestionSelect: (text: string) => void
}

function renderConfidenceBadges(richContent: RichContent[]) {
  const confidence = richContent.find(r => r.type === 'confidence')
  const reviewStatus = richContent.find(r => r.type === 'reviewStatus')

  if (!confidence && !reviewStatus) return null

  return (
    <div className="flex items-center gap-1.5 mb-2">
      {confidence && (
        <Badge variant={confidence.data.score >= 85 ? 'emerald' : confidence.data.score >= 70 ? 'gold' : 'coral'}>
          {confidence.data.score}% {confidence.data.label}
        </Badge>
      )}
      {reviewStatus && (
        <>
          <Badge variant="emerald">{reviewStatus.data.approved} approved</Badge>
          <Badge variant="gray">{reviewStatus.data.draft} draft</Badge>
        </>
      )}
    </div>
  )
}

function renderMiniCharts(richContent: RichContent[]) {
  return richContent
    .filter(r => r.type === 'miniChart')
    .map((r, i) => (
      <div key={`chart-${i}`} className="my-2 flex items-center gap-2">
        <Sparkline data={r.data.values} color={r.data.color} width={80} height={20} />
        <span className="text-[8px] text-tx-tertiary">{r.data.label}</span>
      </div>
    ))
}

function renderVarianceCallouts(richContent: RichContent[]) {
  return richContent
    .filter(r => r.type === 'varianceCallout')
    .map((r, i) => (
      <VarianceCallout
        key={`var-${i}`}
        account={r.data.account}
        delta={r.data.delta}
        description={r.data.description}
        favorable={r.data.favorable}
        status={r.data.status}
      />
    ))
}

function renderNettingAlerts(richContent: RichContent[]) {
  return richContent
    .filter(r => r.type === 'nettingAlert')
    .map((r, i) => (
      <NettingAlert key={`net-${i}`} message={r.data.message} />
    ))
}

function renderDataTables(richContent: RichContent[]) {
  return richContent
    .filter(r => r.type === 'dataTable')
    .map((r, i) => (
      <InlineDataTable key={`tbl-${i}`} columns={r.data.columns} rows={r.data.rows} />
    ))
}

export function AgentMessage({ message, isStreaming, onSuggestionSelect }: AgentMessageProps) {
  const { text, richContent, suggestions } = message

  return (
    <div className="mt-3">
      <div className="flex gap-2 items-start">
        <AgentAvatar isStreaming={isStreaming} />
        <div
          className="flex-1 rounded-[4px_14px_14px_14px] p-3 text-[11px] leading-relaxed text-tx-secondary"
          style={{
            background: 'var(--glass)',
            backdropFilter: 'var(--glass-blur)',
            border: '1px solid var(--glass-border)',
          }}
        >
          {/* Confidence + review status badges */}
          {richContent && renderConfidenceBadges(richContent)}

          {/* Message text with markdown rendering + optional streaming cursor */}
          <div className="whitespace-pre-wrap">{isStreaming ? text : renderMarkdown(text)}</div>
          {isStreaming && <StreamingCursor />}

          {/* Rich content (only after streaming completes) */}
          {richContent && (
            <>
              {renderMiniCharts(richContent)}
              {renderVarianceCallouts(richContent)}
              {renderNettingAlerts(richContent)}
              {renderDataTables(richContent)}
            </>
          )}
        </div>
      </div>

      {/* Suggestion pills below message card */}
      {suggestions && !isStreaming && (
        <div className="ml-8 mt-2">
          <SuggestionPills pills={suggestions} onSelect={onSuggestionSelect} />
        </div>
      )}
    </div>
  )
}
