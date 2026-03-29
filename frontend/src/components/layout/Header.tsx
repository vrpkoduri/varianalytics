import { useLocation } from 'react-router-dom';
import { User } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { cn } from '@/utils/theme';

const ROUTE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/pl': 'P&L View',
  '/chat': 'Chat',
  '/review': 'Review Queue',
  '/approval': 'Approval Queue',
  '/reports': 'Reports',
  '/admin': 'Administration',
};

export default function Header() {
  const location = useLocation();
  const title = ROUTE_TITLES[location.pathname] || 'Variance Agent';

  return (
    <header className="flex h-16 items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-bg-primary)] px-6">
      {/* Page title */}
      <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
        {title}
      </h1>

      {/* Controls */}
      <div className="flex items-center gap-3">
        {/* Period selector placeholder */}
        <div className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm text-[var(--color-text-secondary)]">
          Period: Mar 2026
        </div>

        {/* BU filter placeholder */}
        <div className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm text-[var(--color-text-secondary)]">
          BU: All
        </div>

        {/* Theme toggle */}
        <ThemeToggle />

        {/* User avatar placeholder */}
        <button
          className={cn(
            'flex h-9 w-9 items-center justify-center rounded-full',
            'bg-brand-100 text-brand-700 dark:bg-brand-900 dark:text-brand-300',
            'transition-colors hover:bg-brand-200 dark:hover:bg-brand-800',
          )}
          aria-label="User menu"
        >
          <User className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
}
