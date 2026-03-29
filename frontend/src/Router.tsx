import { createBrowserRouter } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import DashboardView from '@/views/DashboardView'
import PLView from '@/views/PLView'
import ChatView from '@/views/ChatView'
import ReviewView from '@/views/ReviewView'
import ApprovalView from '@/views/ApprovalView'
import ReportsView from '@/views/ReportsView'
import AdminView from '@/views/AdminView'

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <DashboardView /> },
      { path: '/pl', element: <PLView /> },
      { path: '/chat', element: <ChatView /> },
      { path: '/review', element: <ReviewView /> },
      { path: '/approval', element: <ApprovalView /> },
      { path: '/reports', element: <ReportsView /> },
      { path: '/admin', element: <AdminView /> },
    ],
  },
])
