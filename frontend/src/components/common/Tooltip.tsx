import { useState, useRef } from 'react'

interface TooltipProps {
  content: string
  children: React.ReactNode
  position?: 'top' | 'bottom'
}

export function Tooltip({ content, children, position = 'bottom' }: TooltipProps) {
  const [visible, setVisible] = useState(false)
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  const show = () => { timeoutRef.current = setTimeout(() => setVisible(true), 200) }
  const hide = () => { clearTimeout(timeoutRef.current); setVisible(false) }

  return (
    <span className="relative inline-flex" onMouseEnter={show} onMouseLeave={hide}>
      {children}
      {visible && (
        <div
          role="tooltip"
          className={`absolute z-50 px-3 py-2 text-[9px] leading-relaxed max-w-[240px] rounded-lg
            border shadow-lg whitespace-normal pointer-events-none
            ${position === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'} left-1/2 -translate-x-1/2`}
          style={{
            background: 'var(--card)',
            borderColor: 'var(--border)',
            color: 'var(--tx-secondary)',
          }}
        >
          {content}
        </div>
      )}
    </span>
  )
}

// Convenience component for the info icon used throughout
export function InfoTooltip({ content }: { content: string }) {
  return (
    <Tooltip content={content}>
      <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full text-[7px] font-bold cursor-help ml-1"
            style={{ background: 'rgba(0,168,199,.1)', color: 'var(--teal)' }}>
        i
      </span>
    </Tooltip>
  )
}
