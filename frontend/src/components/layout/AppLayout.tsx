import { useState, useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import IdentityBar from './IdentityBar'
import ContextStrip from './ContextStrip'
import Sidebar from './Sidebar'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import { PageTransition } from '@/components/common/PageTransition'
import { cn } from '@/utils/theme'

export default function AppLayout() {
  const location = useLocation()
  const [focusMode, setFocusMode] = useState(false)
  const isChatPage = location.pathname === '/chat'
  const sidebarOpen = !isChatPage && !focusMode

  // Focus mode body class
  useEffect(() => {
    if (focusMode) {
      document.body.classList.add('meeting')
    } else {
      document.body.classList.remove('meeting')
    }
    return () => document.body.classList.remove('meeting')
  }, [focusMode])

  return (
    <div className="flex flex-col h-screen">
      {/* Headers — fade out in focus mode */}
      <div
        style={{ transition: 'opacity 0.25s ease, transform 0.25s ease' }}
        className={focusMode ? 'opacity-0 pointer-events-none h-0 overflow-hidden' : 'opacity-100'}
      >
        <IdentityBar />
        <ContextStrip onFocusToggle={() => setFocusMode(true)} />
      </div>

      {/* Focus mode: show exit button */}
      {focusMode && (
        <button
          onClick={() => setFocusMode(false)}
          className="fixed top-4 right-4 z-50 text-[10px] px-3 py-1.5 rounded-[6px] border border-white/15 bg-[rgba(0,26,77,.6)] backdrop-blur-md text-white/60 hover:text-white hover:border-teal/40 transition-all"
        >
          Exit Focus
        </button>
      )}

      {/* Main: Sidebar + Content */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar isOpen={sidebarOpen} />
        <main
          className={cn(
            'flex-1 overflow-y-auto transition-all duration-300',
            focusMode ? 'px-10 py-6 max-w-full' : 'px-6 py-5 max-w-content'
          )}
        >
          <ErrorBoundary>
            <PageTransition>
              <Outlet />
            </PageTransition>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
