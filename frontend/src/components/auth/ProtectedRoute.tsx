/**
 * Route guard component that enforces authentication and role-based access.
 *
 * Usage:
 *   <ProtectedRoute>                     — any authenticated user
 *   <ProtectedRoute roles={['admin']}>   — admin only
 *   <ProtectedRoute roles={['analyst', 'admin']}> — analyst or admin
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** Required roles (any match = allowed). If empty, any authenticated user is allowed. */
  roles?: string[];
}

export function ProtectedRoute({ children, roles }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  // Show loading state while checking auth
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-bg">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-text-secondary text-sm">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // Not authenticated — redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Role check (if roles specified)
  if (roles && roles.length > 0 && user) {
    const hasRole = roles.some(
      (r) => user.roles.includes(r) || user.roles.includes('admin'),
    );
    if (!hasRole) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  return <>{children}</>;
}
