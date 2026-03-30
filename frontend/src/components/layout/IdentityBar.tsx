import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { cn } from '@/utils/theme'
import ThemeToggle from './ThemeToggle'
import { NotificationDropdown } from './NotificationDropdown'

const TABS = [
  { key: 'dash', label: 'Dashboard', route: '/' },
  { key: 'pl', label: 'P&L', route: '/pl' },
  { key: 'chat', label: 'Chat', route: '/chat' },
  { key: 'review', label: 'Review', route: '/review' },
  { key: 'approve', label: 'Approvals', route: '/approval' },
  { key: 'reports', label: 'Reports', route: '/reports' },
] as const

function useClockTime() {
  const [time, setTime] = useState(() => {
    const now = new Date()
    return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
  })

  useEffect(() => {
    const id = setInterval(() => {
      const now = new Date()
      setTime(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }))
    }, 30000)
    return () => clearInterval(id)
  }, [])

  return time
}

export default function IdentityBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const clock = useClockTime()
  const [notifOpen, setNotifOpen] = useState(false)

  const activeTab = TABS.find((t) => t.route === location.pathname)?.key ?? 'dash'

  return (
    <header
      className="sticky top-0 z-50 flex h-[58px] items-center justify-between px-6"
      style={{
        background: 'linear-gradient(135deg, #002C77, #001A4D, #002C77)',
        backgroundSize: '200% 200%',
        animation: 'headerGrad 8s ease infinite',
      }}
    >
      {/* Left — Logo group */}
      <div className="flex items-center gap-2.5">
        {/* SVG M logo */}
        <svg width="30" height="30" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="15" cy="15" r="14" fill="url(#mgrad)" />
          <path
            d="M8 21V11l4.5 6 4.5-6v10"
            stroke="white"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
          <defs>
            <linearGradient id="mgrad" x1="0" y1="0" x2="30" y2="30" gradientUnits="userSpaceOnUse">
              <stop stopColor="#002C77" />
              <stop offset="1" stopColor="#00A8C7" />
            </linearGradient>
          </defs>
        </svg>
        <div className="flex flex-col">
          <div className="flex items-baseline">
            <span className="font-display text-[18px] font-bold text-white tracking-[0.3px]">
              Marsh
            </span>
            <span className="font-display text-[18px] font-normal text-white/85 tracking-[0.2px] ml-1">
              Vantage
            </span>
          </div>
          <span className="text-[8.5px] font-semibold text-[#A7E2F0]/55 tracking-[2.5px] uppercase mt-[1px]">
            VARIANCE INTELLIGENCE
          </span>
        </div>
      </div>

      {/* Center — Tab navigation */}
      <div className="flex gap-0.5 bg-white/[.06] rounded-[7px] p-[3px] border border-white/[.08]">
        {TABS.map((tab) => {
          const isActive = tab.key === activeTab
          return (
            <button
              key={tab.key}
              onClick={() => navigate(tab.route)}
              className={cn(
                'px-4 py-1.5 rounded-[5px] text-[12px] font-semibold transition-all duration-200',
                isActive
                  ? 'bg-gradient-to-br from-teal to-persian text-white shadow-[0_2px_10px_rgba(0,168,199,.35)]'
                  : 'text-white/40 hover:text-white/70 hover:bg-white/[.04]'
              )}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Right — Controls */}
      <div className="flex items-center gap-3">
        {/* Bell */}
        <div className="relative">
          <div
            className="relative w-[30px] h-[30px] rounded-[7px] border border-white/10 bg-white/[.04] flex items-center justify-center cursor-pointer hover:bg-white/[.08] transition-colors"
            onClick={() => setNotifOpen(!notifOpen)}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-white/50"
            >
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-coral text-white text-[7px] font-bold flex items-center justify-center">
              3
            </span>
          </div>
          <NotificationDropdown isOpen={notifOpen} onClose={() => setNotifOpen(false)} />
        </div>

        {/* Theme toggle */}
        <ThemeToggle />

        {/* Clock */}
        <span className="text-[11px] text-white/30 font-medium tracking-[0.3px] min-w-[56px] text-right">
          {clock}
        </span>
      </div>
    </header>
  )
}
