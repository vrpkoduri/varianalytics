import { useState, useEffect } from 'react'

export function TimestampBar() {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => setElapsed((e) => e + 1), 60_000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="flex items-center gap-2 text-[9px] text-tx-tertiary animate-fade-up d1">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald" />
      </span>
      <span>Actuals as of Jun 30, 2026 18:42 UTC</span>
      <span className="text-tx-tertiary/50">&middot;</span>
      <span>Refreshed {elapsed === 0 ? 'just now' : `${elapsed}m ago`}</span>
    </div>
  )
}
