import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@/context/ThemeContext';
import { UserProvider } from '@/context/UserContext';
import { GlobalFiltersProvider } from '@/context/GlobalFiltersContext';
import { ReviewStatsProvider } from '@/context/ReviewStatsContext';
import AppLayout from '@/components/layout/AppLayout';
import AppRouter from '@/Router';
import { GlobalBackground } from '@/components/layout/GlobalBackground';

export default function App() {
  return (
    <ThemeProvider>
      <GlobalBackground />
      <UserProvider>
        <GlobalFiltersProvider>
          <ReviewStatsProvider>
            <BrowserRouter>
              <AppLayout>
                <AppRouter />
              </AppLayout>
            </BrowserRouter>
          </ReviewStatsProvider>
        </GlobalFiltersProvider>
      </UserProvider>
    </ThemeProvider>
  );
}
