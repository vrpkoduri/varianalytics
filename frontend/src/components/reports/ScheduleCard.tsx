import { GlassCard } from '@/components/common/GlassCard'
import { cn } from '@/utils/theme'
import type { ScheduleItem } from '@/mocks/reportsData'

interface ScheduleCardProps {
  schedule: ScheduleItem
  onToggle: () => void
}

export function ScheduleCard({ schedule, onToggle }: ScheduleCardProps) {
  return (
    <GlassCard className="flex items-center justify-between p-3 px-4">
      <div className="min-w-0">
        <div className="text-[11px] font-semibold truncate">{schedule.name}</div>
        <div className="text-[9px] text-tx-tertiary mt-0.5">
          {schedule.frequency} &middot; Next: {schedule.nextRun}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0 ml-3">
        <button
          onClick={onToggle}
          className={cn(
            'px-2.5 py-0.5 rounded-badge text-[8px] font-semibold transition-colors',
            schedule.isActive
              ? 'bg-emerald-surface text-emerald'
              : 'bg-[rgba(255,255,255,.05)] text-tx-tertiary',
          )}
        >
          {schedule.isActive ? 'Active' : 'Paused'}
        </button>
        <button
          className="px-2.5 py-1 rounded-button text-[8px] font-semibold border border-[rgba(255,255,255,.08)] text-tx-tertiary opacity-50 cursor-not-allowed"
          disabled
        >
          Edit
        </button>
      </div>
    </GlassCard>
  )
}
