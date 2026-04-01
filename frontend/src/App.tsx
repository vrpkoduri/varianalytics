import { useEffect } from 'react'
import { RouterProvider } from 'react-router-dom'
import { ThemeProvider } from '@/context/ThemeContext'
import { AuthProvider } from '@/context/AuthContext'
import { UserProvider } from '@/context/UserContext'
import { GlobalFiltersProvider } from '@/context/GlobalFiltersContext'
import { ReviewStatsProvider } from '@/context/ReviewStatsContext'
import { ModalProvider } from '@/context/ModalContext'
import { GlobalBackground } from '@/components/layout/GlobalBackground'
import { VarianceModal } from '@/components/modal/VarianceModal'
import { ConfettiContainer } from '@/components/common/ConfettiContainer'
import { router } from '@/Router'

// E7: Global keyboard shortcuts
function useGlobalKeyboardShortcuts() {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Escape already handled by modal
      // Future: '?' for help overlay, '/' for search focus, 'g d' for go to dashboard
      if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
        // TODO: Toggle help overlay showing all keyboard shortcuts
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])
}

export default function App() {
  useGlobalKeyboardShortcuts()

  return (
    <ThemeProvider>
      <GlobalBackground />
      <AuthProvider>
        <UserProvider>
          <GlobalFiltersProvider>
            <ReviewStatsProvider>
              <ModalProvider>
                <RouterProvider router={router} />
                <VarianceModal />
                <ConfettiContainer />
              </ModalProvider>
            </ReviewStatsProvider>
          </GlobalFiltersProvider>
        </UserProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
