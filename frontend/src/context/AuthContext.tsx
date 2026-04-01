/**
 * Authentication context provider.
 *
 * Manages JWT tokens, user profile, login/logout state,
 * and automatic token refresh. Replaces UserContext for auth.
 *
 * Tokens are stored in memory (not localStorage) for security.
 * Token refresh happens automatically 5 minutes before expiry.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { api, setAuthToken } from '@/utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuthUser {
  userId: string;
  email: string;
  displayName: string;
  roles: string[];
  buScope: string[];
  persona: string;
  isAdmin: boolean;
}

interface AzureADConfig {
  configured: boolean;
  clientId?: string;
  tenantId?: string;
  authority?: string;
  scopes?: string[];
}

interface AuthContextValue {
  /** Current authenticated user (null if not logged in) */
  user: AuthUser | null;
  /** Whether auth state is being determined */
  isLoading: boolean;
  /** Whether user is authenticated */
  isAuthenticated: boolean;
  /** Azure AD configuration (for login page) */
  azureAdConfig: AzureADConfig;
  /** Login with email and password (dev mode) */
  login: (email: string, password: string) => Promise<void>;
  /** Login with Azure AD authorization code */
  loginWithAzureAD: (code: string, redirectUri: string) => Promise<void>;
  /** Register a new account (dev mode only) */
  register: (email: string, password: string, displayName: string) => Promise<void>;
  /** Log out and clear tokens */
  logout: () => void;
  /** Error message from last auth operation */
  error: string | null;
  /** Clear error */
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [azureAdConfig, setAzureAdConfig] = useState<AzureADConfig>({ configured: false });

  const accessTokenRef = useRef<string | null>(null);
  const refreshTokenRef = useRef<string | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear refresh timer on unmount
  useEffect(() => {
    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, []);

  // Schedule token refresh 5 minutes before expiry
  const scheduleRefresh = useCallback((expiresIn: number) => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    // Refresh 5 minutes before expiry (or half the time if < 10 min)
    const refreshMs = Math.max((expiresIn - 300) * 1000, (expiresIn / 2) * 1000);
    refreshTimerRef.current = setTimeout(async () => {
      try {
        if (!refreshTokenRef.current) return;
        const data = await api.gateway.post<{
          accessToken: string;
          refreshToken: string;
          expiresIn: number;
        }>('/auth/refresh', { refresh_token: refreshTokenRef.current });

        accessTokenRef.current = data.accessToken;
        refreshTokenRef.current = data.refreshToken;
        setAuthToken(data.accessToken);
        scheduleRefresh(data.expiresIn);
      } catch {
        // Refresh failed — user needs to login again
        setUser(null);
        accessTokenRef.current = null;
        refreshTokenRef.current = null;
        setAuthToken(null);
      }
    }, refreshMs);
  }, []);

  // Fetch user profile after token is set
  const fetchUserProfile = useCallback(async () => {
    try {
      const profile = await api.gateway.get<AuthUser>('/auth/me');
      setUser(profile);
    } catch {
      setUser(null);
    }
  }, []);

  // Handle successful token response
  const handleTokenResponse = useCallback(
    async (data: { accessToken: string; refreshToken: string; expiresIn: number }) => {
      accessTokenRef.current = data.accessToken;
      refreshTokenRef.current = data.refreshToken;
      setAuthToken(data.accessToken);
      scheduleRefresh(data.expiresIn);
      await fetchUserProfile();
    },
    [scheduleRefresh, fetchUserProfile],
  );

  // Login with email/password
  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      setIsLoading(true);
      try {
        const data = await api.gateway.post<{
          accessToken: string;
          refreshToken: string;
          expiresIn: number;
        }>('/auth/login', { email, password });
        await handleTokenResponse(data);
      } catch (err: any) {
        const message = err?.detail || err?.message || 'Login failed';
        setError(message);
        throw new Error(message);
      } finally {
        setIsLoading(false);
      }
    },
    [handleTokenResponse],
  );

  // Login with Azure AD
  const loginWithAzureAD = useCallback(
    async (code: string, redirectUri: string) => {
      setError(null);
      setIsLoading(true);
      try {
        const data = await api.gateway.post<{
          accessToken: string;
          refreshToken: string;
          expiresIn: number;
        }>('/auth/login/azure-ad', { code, redirect_uri: redirectUri });
        await handleTokenResponse(data);
      } catch (err: any) {
        const message = err?.detail || err?.message || 'Azure AD login failed';
        setError(message);
        throw new Error(message);
      } finally {
        setIsLoading(false);
      }
    },
    [handleTokenResponse],
  );

  // Register
  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      setError(null);
      try {
        await api.gateway.post('/auth/register', {
          email,
          password,
          display_name: displayName,
        });
        // Auto-login after registration
        await login(email, password);
      } catch (err: any) {
        const message = err?.detail || err?.message || 'Registration failed';
        setError(message);
        throw new Error(message);
      }
    },
    [login],
  );

  // Logout
  const logout = useCallback(() => {
    // Fire-and-forget logout to backend
    if (accessTokenRef.current) {
      api.gateway.post('/auth/logout', {}).catch(() => {});
    }

    accessTokenRef.current = null;
    refreshTokenRef.current = null;
    setAuthToken(null);
    setUser(null);
    setError(null);

    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  // On mount: try to get profile (dev mode auto-login)
  useEffect(() => {
    async function initAuth() {
      try {
        // Fetch Azure AD config
        const adConfig = await api.gateway.get<AzureADConfig>('/auth/azure-ad/config');
        setAzureAdConfig(adConfig);
      } catch {
        // Azure AD config endpoint not available
      }

      try {
        // In dev mode, /auth/me works without token (returns dev user)
        const profile = await api.gateway.get<AuthUser>('/auth/me');
        if (profile?.userId) {
          setUser(profile);
        }
      } catch {
        // Not authenticated — will redirect to login
      } finally {
        setIsLoading(false);
      }
    }

    initAuth();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        azureAdConfig,
        login,
        loginWithAzureAD,
        register,
        logout,
        error,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
