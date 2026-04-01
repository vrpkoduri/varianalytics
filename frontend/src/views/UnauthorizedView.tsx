/**
 * Unauthorized access page.
 *
 * Shown when a user tries to access a page they don't have permission for.
 */

import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

export default function UnauthorizedView() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div
        className="text-center max-w-md p-8 rounded-2xl border border-border/30 animate-fadeUp"
        style={{
          background: 'var(--card)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
        }}
      >
        {/* Gradient stripe */}
        <div
          className="absolute top-0 left-0 right-0 h-0.5 rounded-t-2xl"
          style={{
            background: 'linear-gradient(90deg, var(--coral), var(--amber))',
          }}
        />

        <div className="text-4xl mb-4">&#128274;</div>
        <h1 className="text-xl font-display font-bold text-text mb-2">
          Access Denied
        </h1>
        <p className="text-text-secondary text-sm mb-6">
          You don't have permission to access this page.
          {user && (
            <span className="block mt-1">
              Signed in as <strong className="text-text">{user.displayName}</strong>
              {' '}({user.roles.join(', ')})
            </span>
          )}
        </p>

        <div className="flex gap-3 justify-center">
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90"
            style={{
              background: 'linear-gradient(135deg, var(--cobalt), var(--accent))',
            }}
          >
            Go to Dashboard
          </button>
          <button
            onClick={logout}
            className="px-4 py-2 rounded-lg text-sm font-medium text-text-secondary border border-border hover:bg-surface transition-colors"
          >
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
