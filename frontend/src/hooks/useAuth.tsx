/**
 * Coupon Sentinel - Auth Context (Milestone 4)
 *
 * Holds the current JWT tokens + user profile, persisted to localStorage so
 * a page refresh doesn't log the user out. No silent-refresh-on-expiry loop
 * yet — the access token lasts 30 minutes (backend/auth.py); on expiry the
 * user sees a 401 error and logs in again. That's a real simplification,
 * not a bug: full silent refresh is a reasonable follow-up, not required
 * for a working Milestone 4.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import {
  getProfile,
  loginUser,
  registerUser,
} from '../api/client';
import type { AuthTokens, UserProfile } from '../types';

const STORAGE_KEY = 'coupon-sentinel-auth';

interface StoredAuth {
  accessToken: string;
  refreshToken: string;
}

interface AuthContextValue {
  accessToken: string | null;
  user: UserProfile | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function loadStoredAuth(): StoredAuth | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredAuth) : null;
  } catch {
    return null;
  }
}

function persistAuth(tokens: AuthTokens | null) {
  if (tokens === null) {
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  const stored: StoredAuth = {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProfile = useCallback(async (token: string) => {
    const profile = await getProfile(token);
    setUser(profile);
  }, []);

  useEffect(() => {
    const stored = loadStoredAuth();
    if (!stored) {
      setIsLoading(false);
      return;
    }
    setAccessToken(stored.accessToken);
    loadProfile(stored.accessToken)
      .catch(() => {
        // Stored token is expired/invalid — drop it rather than looping errors.
        persistAuth(null);
        setAccessToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, [loadProfile]);

  const applyTokens = useCallback(
    async (tokens: AuthTokens) => {
      persistAuth(tokens);
      setAccessToken(tokens.access_token);
      await loadProfile(tokens.access_token);
    },
    [loadProfile]
  );

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      try {
        const tokens = await loginUser(email, password);
        await applyTokens(tokens);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Login failed');
        throw err;
      }
    },
    [applyTokens]
  );

  const register = useCallback(
    async (email: string, password: string) => {
      setError(null);
      try {
        const tokens = await registerUser(email, password);
        await applyTokens(tokens);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Registration failed');
        throw err;
      }
    },
    [applyTokens]
  );

  const logout = useCallback(() => {
    persistAuth(null);
    setAccessToken(null);
    setUser(null);
    setError(null);
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!accessToken) return;
    await loadProfile(accessToken);
  }, [accessToken, loadProfile]);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AuthContext.Provider
      value={{ accessToken, user, isLoading, error, login, register, logout, refreshProfile, clearError }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
