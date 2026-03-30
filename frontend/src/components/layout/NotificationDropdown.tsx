import { useState, useRef, useEffect } from 'react'
import { MOCK_NOTIFICATIONS } from '../../mocks/notificationData'

interface NotificationDropdownProps {
  isOpen: boolean
  onClose: () => void
}

export function NotificationDropdown({ isOpen, onClose }: NotificationDropdownProps) {
  const [notifications, setNotifications] = useState(MOCK_NOTIFICATIONS)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Click outside to close
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [isOpen, onClose])

  const markAllRead = () => setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  const unreadCount = notifications.filter(n => !n.read).length

  if (!isOpen) return null

  return (
    <div ref={dropdownRef}
         className="absolute top-full right-0 mt-2 w-[280px] max-h-[320px] overflow-y-auto rounded-lg border shadow-xl z-50 animate-slide-down"
         style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
        <span className="text-[10px] font-bold" style={{ color: 'var(--tx-primary)' }}>
          Notifications {unreadCount > 0 && <span className="text-teal">({unreadCount})</span>}
        </span>
        {unreadCount > 0 && (
          <button onClick={markAllRead} className="text-[8px] font-semibold" style={{ color: 'var(--teal)' }}>
            Mark all read
          </button>
        )}
      </div>
      {/* Items */}
      {notifications.map(n => (
        <div key={n.id} className="flex items-start gap-2 px-3 py-2 border-b cursor-pointer transition-colors"
             style={{ borderColor: 'var(--border)', background: n.read ? 'transparent' : 'rgba(0,168,199,.03)' }}>
          {!n.read && <span className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{ background: 'var(--teal)' }} />}
          {n.read && <span className="w-1.5 h-1.5 flex-shrink-0" />}
          <div className="flex-1 min-w-0">
            <div className="text-[10px] leading-snug" style={{ color: n.read ? 'var(--tx-tertiary)' : 'var(--tx-secondary)' }}>
              {n.text}
            </div>
            <div className="text-[8px] mt-0.5" style={{ color: 'var(--tx-tertiary)' }}>{n.time}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
