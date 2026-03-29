import { RouterProvider } from 'react-router-dom'
import { ThemeProvider } from '@/context/ThemeContext'
import { UserProvider } from '@/context/UserContext'
import { GlobalFiltersProvider } from '@/context/GlobalFiltersContext'
import { ReviewStatsProvider } from '@/context/ReviewStatsContext'
import { GlobalBackground } from '@/components/layout/GlobalBackground'
import { router } from '@/Router'

export default function App() {
  return (
    <ThemeProvider>
      <GlobalBackground />
      <UserProvider>
        <GlobalFiltersProvider>
          <ReviewStatsProvider>
            <RouterProvider router={router} />
          </ReviewStatsProvider>
        </GlobalFiltersProvider>
      </UserProvider>
    </ThemeProvider>
  )
}
