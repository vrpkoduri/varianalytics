import { useCallback, useRef, useState } from 'react'
import { matchIntent, MOCK_RESPONSES, type RichContent } from '@/mocks/chatData'

export interface ChatMessage {
  id: string
  role: 'user' | 'agent'
  text: string
  isStreaming?: boolean
  isTyping?: boolean
  richContent?: RichContent[]
  suggestions?: string[]
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const streamRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const sendMessage = useCallback((text: string) => {
    if (isStreaming) return

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', text }
    const agentMsg: ChatMessage = { id: crypto.randomUUID(), role: 'agent', text: '', isTyping: true }

    setMessages(prev => [...prev, userMsg, agentMsg])
    setIsStreaming(true)

    // Match intent
    const intent = matchIntent(text)
    const response = MOCK_RESPONSES[intent] || MOCK_RESPONSES.default

    // 800ms typing indicator, then stream
    setTimeout(() => {
      const chars = response.text.split('')
      let index = 0

      setMessages(prev => prev.map(m =>
        m.id === agentMsg.id ? { ...m, isTyping: false, isStreaming: true } : m
      ))

      const tick = () => {
        index += 3
        const currentText = chars.slice(0, index).join('')
        const done = index >= chars.length

        setMessages(prev => prev.map(m =>
          m.id === agentMsg.id ? {
            ...m,
            text: done ? response.text : currentText,
            isStreaming: !done,
            richContent: done ? response.richContent : undefined,
            suggestions: done ? response.suggestions : undefined,
          } : m
        ))

        if (done) {
          setIsStreaming(false)
        } else {
          streamRef.current = setTimeout(tick, 15 + Math.random() * 20)
        }
      }
      tick()
    }, 800)
  }, [isStreaming])

  const clearChat = useCallback(() => {
    if (streamRef.current) clearTimeout(streamRef.current)
    setMessages([])
    setIsStreaming(false)
  }, [])

  return { messages, isStreaming, sendMessage, clearChat }
}
