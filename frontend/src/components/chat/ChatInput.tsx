import { useState, type KeyboardEvent } from 'react'
import { cn } from '@/utils/theme'

interface ChatInputProps {
  onSend: (text: string) => void
  disabled: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [inputValue, setInputValue] = useState('')

  const handleSend = () => {
    const trimmed = inputValue.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setInputValue('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex gap-1.5">
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about variances..."
        disabled={disabled}
        className={cn(
          'flex-1 py-2.5 px-3.5 rounded-lg border border-border bg-card text-[11px] text-tx-primary outline-none transition-all',
          'placeholder:text-tx-tertiary',
          'focus:border-teal focus:shadow-[0_0_0_3px_rgba(0,168,199,.1)]',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !inputValue.trim()}
        className={cn(
          'px-4 py-1.5 rounded-md text-[10px] font-semibold text-white transition-all',
          disabled || !inputValue.trim()
            ? 'opacity-50 cursor-not-allowed'
            : 'hover:shadow-[0_2px_8px_rgba(0,168,199,.3)]'
        )}
        style={{ background: 'linear-gradient(135deg, #002C77, #00A8C7)' }}
      >
        Send
      </button>
    </div>
  )
}
