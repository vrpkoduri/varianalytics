import { cn } from '@/utils/theme'

type TabKey = 'reports' | 'schedules' | 'templates'

interface ReportSubTabsProps {
  activeTab: TabKey
  onTabChange: (tab: TabKey) => void
}

const TABS: { key: TabKey; label: string }[] = [
  { key: 'reports', label: 'Reports' },
  { key: 'schedules', label: 'Schedules' },
  { key: 'templates', label: 'Templates' },
]

export function ReportSubTabs({ activeTab, onTabChange }: ReportSubTabsProps) {
  return (
    <div className="flex gap-0.5 bg-[rgba(255,255,255,.06)] rounded-lg p-0.5 border border-[rgba(255,255,255,.08)] mb-4">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onTabChange(tab.key)}
          className={cn(
            'px-4 py-1.5 rounded-md text-[10px] font-semibold transition-all duration-150',
            activeTab === tab.key
              ? 'bg-gradient-to-r from-teal to-[#016D9E] text-white shadow-[0_2px_10px_rgba(0,168,199,.35)]'
              : 'text-[rgba(255,255,255,.4)] hover:text-[rgba(255,255,255,.7)] hover:bg-[rgba(255,255,255,.04)]',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
