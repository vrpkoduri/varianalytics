import { useCallback, useEffect, useRef } from 'react'
import { useUser } from '@/context/UserContext'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'
import { useChat } from '@/hooks/useChat'
import { useSSE, type SSEEvent } from '@/hooks/useSSE'
import { ChatHeader } from '@/components/chat/ChatHeader'
import { UserMessage } from '@/components/chat/UserMessage'
import { AgentAvatar } from '@/components/chat/AgentAvatar'
import { AgentMessage } from '@/components/chat/AgentMessage'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import { ChatInput } from '@/components/chat/ChatInput'

export default function ChatView() {
  const { persona } = useUser()
  const { filters } = useGlobalFilters()
  const { messages, isStreaming, sendMessage, clearChat, conversationId, useRealApi, setMessages, setIsStreaming, sseKey } = useChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const prevPersona = useRef(persona)

  // SSE handler for real API mode — updates the last agent message with streamed tokens
  const handleSSEEvent = useCallback((event: SSEEvent) => {
    switch (event.type) {
      case 'token':
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last && last.role === 'agent') {
            return [...updated.slice(0, -1), { ...last, text: last.text + (event.payload.text || ''), isStreaming: true, isTyping: false }]
          }
          return updated
        })
        break
      case 'done':
        setMessages(prev => prev.map(m => m.isStreaming ? { ...m, isStreaming: false } : m))
        setIsStreaming(false)
        break
      case 'suggestion':
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last?.role === 'agent') {
            return [...prev.slice(0, -1), { ...last, suggestions: event.payload.suggestions }]
          }
          return prev
        })
        break
      case 'error':
        // Connection error — mark streaming complete
        setMessages(prev => prev.map(m => m.isStreaming || m.isTyping ? { ...m, isStreaming: false, isTyping: false } : m))
        setIsStreaming(false)
        break
    }
  }, [setMessages, setIsStreaming])

  useSSE(
    conversationId,
    handleSSEEvent,
    useRealApi && !!conversationId,
    sseKey,
  )

  // Clear chat on persona switch
  useEffect(() => {
    if (prevPersona.current !== persona) {
      clearChat()
      prevPersona.current = persona
    }
  }, [persona, clearChat])

  // Auto-scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = (text: string) => sendMessage(text)

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-0">
        {persona === 'bu' && (
          <div
            className="px-3 py-1.5 rounded-lg text-[9px] animate-fade-up mb-2"
            style={{
              background: 'rgba(0,168,199,.06)',
              border: '1px solid rgba(0,168,199,.12)',
            }}
          >
            <span className="font-semibold" style={{ color: 'var(--teal)' }}>&#128274; Marsh</span>
            <span className="ml-1" style={{ color: 'var(--tx-secondary)' }}>Showing data scoped to your business unit</span>
          </div>
        )}
        <ChatHeader
          persona={persona}
          viewType={filters.viewType}
          comparisonBase={filters.comparisonBase}
          hasMessages={messages.length > 0}
          onSuggestionSelect={handleSend}
        />

        {messages.map((msg) =>
          msg.role === 'user' ? (
            <UserMessage key={msg.id} text={msg.text} />
          ) : msg.isTyping ? (
            <div key={msg.id} className="flex gap-2 items-start mt-3">
              <AgentAvatar isStreaming />
              <div
                className="p-3 rounded-[4px_14px_14px_14px]"
                style={{
                  background: 'var(--glass)',
                  backdropFilter: 'var(--glass-blur)',
                  border: '1px solid var(--glass-border)',
                }}
              >
                <TypingIndicator />
              </div>
            </div>
          ) : (
            <AgentMessage
              key={msg.id}
              message={msg}
              isStreaming={msg.isStreaming || false}
              onSuggestionSelect={handleSend}
            />
          )
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="px-4 py-3 border-t border-border">
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  )
}
