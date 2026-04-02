import { createBrowserRouter } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import DashboardView from '@/views/DashboardView'
import PLView from '@/views/PLView'
import ChatView from '@/views/ChatView'
import ReviewView from '@/views/ReviewView'
import ApprovalView from '@/views/ApprovalView'
import ReportsView from '@/views/ReportsView'
import AdminView from '@/views/AdminView'
import ExecSummaryView from '@/views/ExecSummaryView'
import LoginView from '@/views/LoginView'
import UnauthorizedView from '@/views/UnauthorizedView'

export const router = createBrowserRouter([
  // Public routes
  { path: '/login', element: <LoginView /> },
  { path: '/unauthorized', element: <UnauthorizedView /> },

  // Protected routes (require authentication)
  {
    element: <AppLayout />,
    children: [
      {
        path: '/',
        element: (
          <ProtectedRoute>
            <DashboardView />
          </ProtectedRoute>
        ),
      },
      {
        path: '/executive',
        element: (
          <ProtectedRoute roles={['director', 'cfo', 'admin']}>
            <ExecSummaryView />
          </ProtectedRoute>
        ),
      },
      {
        path: '/pl',
        element: (
          <ProtectedRoute>
            <PLView />
          </ProtectedRoute>
        ),
      },
      {
        path: '/chat',
        element: (
          <ProtectedRoute>
            <ChatView />
          </ProtectedRoute>
        ),
      },
      {
        path: '/review',
        element: (
          <ProtectedRoute roles={['analyst', 'admin']}>
            <ReviewView />
          </ProtectedRoute>
        ),
      },
      {
        path: '/approval',
        element: (
          <ProtectedRoute roles={['director', 'cfo', 'admin']}>
            <ApprovalView />
          </ProtectedRoute>
        ),
      },
      {
        path: '/reports',
        element: (
          <ProtectedRoute>
            <ReportsView />
          </ProtectedRoute>
        ),
      },
      {
        path: '/admin',
        element: (
          <ProtectedRoute roles={['admin']}>
            <AdminView />
          </ProtectedRoute>
        ),
      },
    ],
  },
])
