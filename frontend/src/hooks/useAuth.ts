import { useState, useCallback } from 'react';

interface UseAuthResult {
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
  login: () => Promise<void>;
  logout: () => void;
}

/**
 * Custom hook for authentication state management.
 * Will integrate with Azure AD (Entra ID) OAuth 2.0 flow.
 */
export function useAuth(): UseAuthResult {
  const [isAuthenticated, setIsAuthenticated] = useState(true); // Default true for dev
  const [isLoading] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  const login = useCallback(async () => {
    // TODO: Implement Azure AD OAuth 2.0 login flow
    // 1. Redirect to Azure AD authorization endpoint
    // 2. Handle callback with authorization code
    // 3. Exchange code for tokens
    // 4. Store tokens securely
    setIsAuthenticated(true);
    setToken('dev-token');
  }, []);

  const logout = useCallback(() => {
    // TODO: Implement logout flow
    // 1. Clear tokens
    // 2. Redirect to Azure AD logout endpoint
    setIsAuthenticated(false);
    setToken(null);
  }, []);

  return { isAuthenticated, isLoading, token, login, logout };
}
