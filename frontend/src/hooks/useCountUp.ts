import { useEffect, useState } from 'react'

/**
 * Animates a number from 0 to the target value over the given duration.
 */
export function useCountUp(target: number, duration = 800): number {
  const [current, setCurrent] = useState(0)

  useEffect(() => {
    if (target === 0) {
      setCurrent(0)
      return
    }

    const stepMs = 16
    const totalSteps = Math.max(Math.floor(duration / stepMs), 1)
    let step = 0

    const interval = setInterval(() => {
      step += 1
      if (step >= totalSteps) {
        setCurrent(target)
        clearInterval(interval)
      } else {
        setCurrent(Math.round((target * step) / totalSteps))
      }
    }, stepMs)

    return () => clearInterval(interval)
  }, [target, duration])

  return current
}
