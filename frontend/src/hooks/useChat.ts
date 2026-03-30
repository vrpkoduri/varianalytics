import { useCallback, useRef, useState } from 'react'
import { matchIntent, MOCK_RESPONSES, type RichContent } from '@/mocks/chatData'
import { api } from '@/utils/api'

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
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [useRealApi, setUseRealApi] = useState(true)
  const streamRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /** Mock streaming fallback — existing logic preserved */
  const sendMessageMock = useCallback(
    (text: string, userMsg?: ChatMessage) => {
      const user =
        userMsg ?? ({ id: crypto.randomUUID(), role: 'user', text } as ChatMessage)
      const agentMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'agent',
        text: '',
        isTyping: true,
      }

      // Only add user message if not already added
      if (!userMsg) {
        setMessages((prev) => [...prev, user, agentMsg])
      } else {
        setMessages((prev) => [...prev, agentMsg])
      }
      setIsStreaming(true)

      // Match intent
      const intent = matchIntent(text)
      const response = MOCK_RESPONSES[intent] || MOCK_RESPONSES.default

      // 800ms typing indicator, then stream
      setTimeout(() => {
        const chars = response.text.split('')
        let index = 0

        setMessages((prev) =>
          prev.map((m) =>
            m.id === agentMsg.id
              ? { ...m, isTyping: false, isStreaming: true }
              : m,
          ),
        )

        const tick = () => {
          index += 3
          const currentText = chars.slice(0, index).join('')
          const done = index >= chars.length

          setMessages((prev) =>
            prev.map((m) =>
              m.id === agentMsg.id
                ? {
                    ...m,
                    text: done ? response.text : currentText,
                    isStreaming: !done,
                    richContent: done ? response.richContent : undefined,
                    suggestions: done ? response.suggestions : undefined,
                  }
                : m,
            ),
          )

          if (done) {
            setIsStreaming(false)
          } else {
            streamRef.current = setTimeout(tick, 15 + Math.random() * 20)
          }
        }
        tick()
      }, 800)
    },
    [],
  )

  /** Try real API first, fall back to mock */
  const sendMessageReal = useCallback(
    async (text: string): Promise<string | null> => {
      try {
        const resp = (await api.gateway.post('/chat/messages', {
          message: text,
          context: { period_id: '2026-06', view_id: 'MTD', base_id: 'BUDGET' },
          conversation_id: conversationId,
        })) as any
        const cid = resp.conversationId || resp.conversation_id
        setConversationId(cid)
        // SSE will be handled by useSSE hook in ChatView
        return cid
      } catch {
        setUseRealApi(false)
        return null // Signals fallback to mock
      }
    },
    [conversationId],
  )

  const sendMessage = useCallback(
    (text: string) => {
      if (isStreaming) return

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        text,
      }
      setMessages((prev) => [...prev, userMsg])

      if (!useRealApi) {
        sendMessageMock(text, userMsg)
        return
      }

      sendMessageReal(text).then((cid) => {
        if (!cid) {
          sendMessageMock(text, userMsg)
        } else {
          // Real API succeeded — agent message will arrive via SSE
          const agentMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'agent',
            text: '',
            isTyping: true,
          }
          setMessages((prev) => [...prev, agentMsg])
          setIsStreaming(true)
        }
      })
    },
    [isStreaming, useRealApi, sendMessageMock, sendMessageReal],
  )

  const clearChat = useCallback(() => {
    if (streamRef.current) clearTimeout(streamRef.current)
    setMessages([])
    setIsStreaming(false)
    setConversationId(null)
    setUseRealApi(true)
  }, [])

  return { messages, isStreaming, sendMessage, clearChat, conversationId, useRealApi }
}
