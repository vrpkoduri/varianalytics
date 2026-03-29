import { RouterProvider } from 'react-router-dom'
import { ThemeProvider } from '@/context/ThemeContext'
import { UserProvider } from '@/context/UserContext'
import { GlobalFiltersProvider } from '@/context/GlobalFiltersContext'
import { ReviewStatsProvider } from '@/context/ReviewStatsContext'
import { ModalProvider } from '@/context/ModalContext'
import { GlobalBackground } from '@/components/layout/GlobalBackground'
import { VarianceModal } from '@/components/modal/VarianceModal'
import { ConfettiContainer } from '@/components/common/ConfettiContainer'
import { router } from '@/Router'

export default function App() {
  return (
    <ThemeProvider>
      <GlobalBackground />
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
    </ThemeProvider>
  )
}
