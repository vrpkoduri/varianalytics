/**
 * Login page with Marsh Vantage branding.
 *
 * Supports two modes:
 * - Dev mode: email + password form
 * - Azure AD: "Sign in with Microsoft" button (when configured)
 */

import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

export default function LoginView() {
  const { login, register, error, clearError, azureAdConfig, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const from = (location.state as any)?.from?.pathname || '/';

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);
    clearError();

    try {
      if (isRegistering) {
        await register(email, password, displayName);
      } else {
        await login(email, password);
      }
      navigate(from, { replace: true });
    } catch (err: any) {
      setLocalError(err.message);
    }
  }

  const displayError = localError || error;

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      {/* Animated background gradient */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute -top-40 -right-40 w-96 h-96 rounded-full opacity-10"
          style={{
            background: 'radial-gradient(circle, var(--accent) 0%, transparent 70%)',
            animation: 'breathe 8s ease-in-out infinite',
          }}
        />
        <div
          className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full opacity-10"
          style={{
            background: 'radial-gradient(circle, var(--cobalt) 0%, transparent 70%)',
            animation: 'breathe 8s ease-in-out infinite 4s',
          }}
        />
      </div>

      {/* Login card */}
      <div
        className="relative w-full max-w-md p-8 rounded-2xl border border-border/30 animate-fadeUp"
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
            background: 'linear-gradient(90deg, var(--cobalt), var(--accent))',
          }}
        />

        {/* Logo / Branding */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-body font-bold text-text mb-1">
            Marsh Vantage
          </h1>
          <p className="text-sm text-text-secondary">
            FP&A Variance Analysis Platform
          </p>
        </div>

        {/* Error message */}
        {displayError && (
          <div className="mb-4 p-3 rounded-lg bg-coral/10 border border-coral/30 text-coral text-sm">
            {displayError}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegistering && (
            <div>
              <label className="block text-sm text-text-secondary mb-1" htmlFor="displayName">
                Display Name
              </label>
              <input
                id="displayName"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                className="w-full px-3 py-2.5 rounded-lg bg-surface border border-border text-text placeholder-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-colors"
                placeholder="Your name"
              />
            </div>
          )}

          <div>
            <label className="block text-sm text-text-secondary mb-1" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2.5 rounded-lg bg-surface border border-border text-text placeholder-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-colors"
              placeholder="analyst@variance-agent.dev"
            />
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-1" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full px-3 py-2.5 rounded-lg bg-surface border border-border text-text placeholder-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-colors"
              placeholder="Enter password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 rounded-lg font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
            style={{
              background: 'linear-gradient(135deg, #002C77, #00A8C7)',
            }}
          >
            {isLoading ? 'Signing in...' : isRegistering ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        {/* Toggle register / login */}
        <div className="mt-4 text-center">
          <button
            type="button"
            onClick={() => {
              setIsRegistering(!isRegistering);
              clearError();
              setLocalError(null);
            }}
            className="text-sm text-accent hover:underline"
          >
            {isRegistering
              ? 'Already have an account? Sign in'
              : 'Need an account? Register'}
          </button>
        </div>

        {/* Azure AD button */}
        {azureAdConfig.configured && (
          <>
            <div className="my-6 flex items-center gap-3">
              <div className="flex-1 h-px bg-border" />
              <span className="text-xs text-text-secondary uppercase tracking-wider">or</span>
              <div className="flex-1 h-px bg-border" />
            </div>

            <button
              type="button"
              onClick={() => {
                // Redirect to Azure AD login
                if (azureAdConfig.authority) {
                  const redirectUri = `${window.location.origin}/auth/callback`;
                  const url = `${azureAdConfig.authority}/oauth2/v2.0/authorize?client_id=${azureAdConfig.clientId}&response_type=code&redirect_uri=${encodeURIComponent(redirectUri)}&scope=openid+profile+email+User.Read&response_mode=query`;
                  window.location.href = url;
                }
              }}
              className="w-full py-2.5 rounded-lg border border-border bg-surface text-text font-medium hover:bg-surface/80 transition-colors flex items-center justify-center gap-2"
            >
              <svg width="20" height="20" viewBox="0 0 21 21" fill="none">
                <rect x="1" y="1" width="9" height="9" fill="#F25022" />
                <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
                <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
                <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
              </svg>
              Sign in with Microsoft
            </button>
          </>
        )}

        {/* Demo credentials hint */}
        <div className="mt-6 p-3 rounded-lg bg-surface border border-border/50">
          <p className="text-xs text-text-secondary mb-2 font-medium">Demo Credentials:</p>
          <div className="grid grid-cols-2 gap-1 text-xs text-text-secondary">
            <span>Admin:</span><span>admin@variance-agent.dev</span>
            <span>Analyst:</span><span>analyst@variance-agent.dev</span>
            <span>Director:</span><span>director@variance-agent.dev</span>
            <span>CFO:</span><span>cfo@variance-agent.dev</span>
            <span className="col-span-2 mt-1 text-accent/70">Password: password123</span>
          </div>
        </div>
      </div>
    </div>
  );
}
