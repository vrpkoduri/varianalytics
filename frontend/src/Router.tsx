import { Routes, Route } from 'react-router-dom';
import DashboardView from '@/views/DashboardView';
import PLView from '@/views/PLView';
import ChatView from '@/views/ChatView';
import ReviewView from '@/views/ReviewView';
import ApprovalView from '@/views/ApprovalView';
import ReportsView from '@/views/ReportsView';
import AdminView from '@/views/AdminView';

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<DashboardView />} />
      <Route path="/pl" element={<PLView />} />
      <Route path="/chat" element={<ChatView />} />
      <Route path="/review" element={<ReviewView />} />
      <Route path="/approval" element={<ApprovalView />} />
      <Route path="/reports" element={<ReportsView />} />
      <Route path="/admin" element={<AdminView />} />
    </Routes>
  );
}
