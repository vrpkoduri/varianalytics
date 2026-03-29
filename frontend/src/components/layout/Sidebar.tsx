import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Table2,
  MessageSquare,
  ClipboardCheck,
  CheckCircle2,
  FileBarChart,
  Settings,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/utils/theme';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: <LayoutDashboard className="h-5 w-5" /> },
  { path: '/pl', label: 'P&L View', icon: <Table2 className="h-5 w-5" /> },
  { path: '/chat', label: 'Chat', icon: <MessageSquare className="h-5 w-5" /> },
  { path: '/review', label: 'Review', icon: <ClipboardCheck className="h-5 w-5" /> },
  { path: '/approval', label: 'Approval', icon: <CheckCircle2 className="h-5 w-5" /> },
  { path: '/reports', label: 'Reports', icon: <FileBarChart className="h-5 w-5" /> },
  { path: '/admin', label: 'Admin', icon: <Settings className="h-5 w-5" /> },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        'flex flex-col border-r border-[var(--color-border)] bg-[var(--color-sidebar-bg)] text-[var(--color-sidebar-text)] transition-all duration-200',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      {/* Logo area */}
      <div className="flex h-16 items-center gap-2 border-b border-white/10 px-4">
        <TrendingUp className="h-6 w-6 shrink-0 text-brand-500" />
        {!collapsed && (
          <span className="text-lg font-semibold tracking-tight text-white">
            Variance Agent
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-[var(--color-sidebar-active)] text-white'
                  : 'text-[var(--color-sidebar-text)] hover:bg-white/10 hover:text-white',
                collapsed && 'justify-center px-2',
              )
            }
          >
            {item.icon}
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center border-t border-white/10 p-3 text-[var(--color-sidebar-text)] transition-colors hover:bg-white/10 hover:text-white"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
      </button>
    </aside>
  );
}
