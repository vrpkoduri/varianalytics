import { useState, useEffect } from 'react'
import { useGlobalFilters } from '@/context/GlobalFiltersContext'

const MONTH_NAMES = [
  '', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

function lastDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

export function TimestampBar() {
  const { filters } = useGlobalFilters()
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    setElapsed(0) // Reset on period change
    const timer = setInterval(() => setElapsed((e) => e + 1), 60_000)
    return () => clearInterval(timer)
  }, [filters.period])

  const year = filters.period?.year || 2026
  const month = filters.period?.month || 6
  const day = lastDayOfMonth(year, month)
  const monthName = MONTH_NAMES[month]

  return (
    <div className="flex items-center gap-2 text-[9px] text-tx-tertiary animate-fade-up d1">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald" />
      </span>
      <span>Actuals as of {monthName} {day}, {year} 18:42 UTC</span>
      <span className="text-tx-tertiary/50">&middot;</span>
      <span>Refreshed {elapsed === 0 ? 'just now' : `${elapsed}m ago`}</span>
    </div>
  )
}
