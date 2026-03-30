import { useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'

export function PageTransition({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const [opacity, setOpacity] = useState(1)
  const [currentChildren, setCurrentChildren] = useState(children)

  useEffect(() => {
    setOpacity(0.3)
    const timer = setTimeout(() => {
      setCurrentChildren(children)
      setOpacity(1)
    }, 150)
    return () => clearTimeout(timer)
  }, [location.pathname]) // Only trigger on route change

  // Also update children immediately when not transitioning
  useEffect(() => {
    setCurrentChildren(children)
  }, [children])

  return (
    <div style={{ opacity, transition: 'opacity 150ms ease' }}>
      {currentChildren}
    </div>
  )
}
