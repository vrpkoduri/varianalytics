/**
 * Lightweight markdown-to-JSX renderer for chat agent responses.
 *
 * Handles: **bold**, ## headers, - bullet lists, \n line breaks,
 * *italic*, `code`. No external dependencies.
 */
import { type ReactNode } from 'react'

/**
 * Convert a markdown string to React elements.
 */
export function renderMarkdown(text: string): ReactNode {
  if (!text) return null

  const lines = text.split('\n')
  const elements: ReactNode[] = []
  let listItems: string[] = []

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="list-disc pl-4 my-1 space-y-0.5">
          {listItems.map((item, i) => (
            <li key={i}>{formatInline(item)}</li>
          ))}
        </ul>
      )
      listItems = []
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    // Blank line
    if (!trimmed) {
      flushList()
      elements.push(<br key={`br-${i}`} />)
      continue
    }

    // ## Header
    if (trimmed.startsWith('## ')) {
      flushList()
      elements.push(
        <div key={`h-${i}`} className="font-bold text-tx-primary text-[12px] mt-2 mb-1">
          {formatInline(trimmed.slice(3))}
        </div>
      )
      continue
    }

    // # Header
    if (trimmed.startsWith('# ')) {
      flushList()
      elements.push(
        <div key={`h1-${i}`} className="font-bold text-tx-primary text-[13px] mt-2 mb-1">
          {formatInline(trimmed.slice(2))}
        </div>
      )
      continue
    }

    // Bullet list item (- or *)
    if (/^[-*]\s/.test(trimmed)) {
      listItems.push(trimmed.slice(2).trim())
      continue
    }

    // Numbered list item (1. 2. etc.)
    if (/^\d+\.\s/.test(trimmed)) {
      listItems.push(trimmed.replace(/^\d+\.\s/, '').trim())
      continue
    }

    // Regular paragraph
    flushList()
    elements.push(
      <div key={`p-${i}`} className="my-0.5">
        {formatInline(trimmed)}
      </div>
    )
  }

  flushList()
  return <>{elements}</>
}

/**
 * Format inline markdown: **bold**, *italic*, `code`
 */
function formatInline(text: string): ReactNode {
  if (!text) return null

  // Split by **bold**, *italic*, `code` patterns
  const parts: ReactNode[] = []
  let remaining = text
  let key = 0

  while (remaining.length > 0) {
    // **bold**
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/)
    // `code`
    const codeMatch = remaining.match(/`([^`]+)`/)
    // *italic* (but not **)
    const italicMatch = remaining.match(/(?<!\*)\*([^*]+)\*(?!\*)/)

    // Find the earliest match
    const matches = [
      boldMatch ? { type: 'bold', match: boldMatch } : null,
      codeMatch ? { type: 'code', match: codeMatch } : null,
      italicMatch ? { type: 'italic', match: italicMatch } : null,
    ].filter(Boolean).sort((a, b) => (a!.match.index ?? 0) - (b!.match.index ?? 0))

    if (matches.length === 0) {
      parts.push(remaining)
      break
    }

    const first = matches[0]!
    const idx = first.match.index ?? 0

    // Text before the match
    if (idx > 0) {
      parts.push(remaining.slice(0, idx))
    }

    // The formatted element
    if (first.type === 'bold') {
      parts.push(<strong key={key++}>{first.match[1]}</strong>)
    } else if (first.type === 'code') {
      parts.push(
        <code key={key++} className="px-1 py-0.5 rounded bg-surface text-teal text-[10px] font-mono">
          {first.match[1]}
        </code>
      )
    } else if (first.type === 'italic') {
      parts.push(<em key={key++}>{first.match[1]}</em>)
    }

    remaining = remaining.slice(idx + first.match[0].length)
  }

  return <>{parts}</>
}
