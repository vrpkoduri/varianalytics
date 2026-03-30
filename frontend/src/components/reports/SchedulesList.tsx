import { useState } from 'react'
import { ScheduleCard } from './ScheduleCard'
import type { ScheduleItem } from '@/mocks/reportsData'

interface SchedulesListProps {
  schedules: ScheduleItem[]
}

export function SchedulesList({ schedules: initial }: SchedulesListProps) {
  const [schedules, setSchedules] = useState(initial)

  const handleToggle = (id: string) => {
    setSchedules((prev) =>
      prev.map((s) => (s.id === id ? { ...s, isActive: !s.isActive } : s)),
    )
  }

  return (
    <div className="space-y-2.5">
      {schedules.map((s) => (
        <ScheduleCard key={s.id} schedule={s} onToggle={() => handleToggle(s.id)} />
      ))}
    </div>
  )
}
