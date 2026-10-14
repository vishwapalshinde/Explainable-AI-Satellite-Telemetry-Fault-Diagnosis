/**
 * Authentication Store
 * 
 * Manages:
 * - Current user information
 * - Authentication status
 * - User permissions/role
 * - Login/logout actions
 * - Token validation
 */

'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * User type from backend response
 */
export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

/**
 * Auth state interface
 */
interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setUser: (user: User) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
  logout: () => void;
  initializeFromStorage: () => void;
  hasPermission: (permission: string) => boolean;
  isAdmin: () => boolean;
}

/**
 * Role-based permission matrix
 */
const ROLE_PERMISSIONS: Record<string, string[]> = {
  admin: [
    'view_telemetry',
    'diagnose_faults',
    'chat',
    'download_data',
    'manage_users',
    'manage_roles',
  ],
  engineer: [
    'view_telemetry',
    'diagnose_faults',
    'chat',
    'download_data',
  ],
  viewer: [
    'view_telemetry',
  ],
};

/**
 * Zustand auth store with persistence
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      // Set user information
      setUser: (user: User) => {
        set({
          user,
          isAuthenticated: true,
        });
        // Also update localStorage for persistence
        localStorage.setItem('user', JSON.stringify(user));
      },

      // Set JWT tokens
      setTokens: (accessToken: string, refreshToken: string) => {
        set({
          accessToken,
          refreshToken,
          isAuthenticated: true,
        });
        // Store in localStorage
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
      },

      // Clear all auth data
      clearAuth: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
        // Clear localStorage
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
      },

      // Logout
      logout: () => {
        const { clearAuth } = get();
        clearAuth();
      },

      // Initialize from localStorage on app load
      initializeFromStorage: () => {
        if (typeof window === 'undefined') return;

        const storedUser = localStorage.getItem('user');
        const storedAccessToken = localStorage.getItem('access_token');
        const storedRefreshToken = localStorage.getItem('refresh_token');

        if (storedUser && storedAccessToken) {
          try {
            const user = JSON.parse(storedUser);
            set({
              user,
              accessToken: storedAccessToken,
              refreshToken: storedRefreshToken,
              isAuthenticated: true,
            });
          } catch (error) {
            console.error('Failed to parse stored auth data:', error);
            get().clearAuth();
          }
        }
      },

      // Check if user has specific permission
      hasPermission: (permission: string): boolean => {
        const { user } = get();
        if (!user) return false;

        const permissions = ROLE_PERMISSIONS[user.role] || [];
        return permissions.includes(permission);
      },

      // Check if user is admin
      isAdmin: (): boolean => {
        const { user } = get();
        return user?.role === 'admin' || false;
      },
    }),
    {
      name: 'auth-storage', // localStorage key
    }
  )
);

/**
 * Custom hook to check permissions
 */
export const useHasPermission = (permission: string) => {
  const hasPermission = useAuthStore((state) => state.hasPermission);
  return hasPermission(permission);
};

/**
 * Custom hook to check if admin
 */
export const useIsAdmin = () => {
  const isAdmin = useAuthStore((state) => state.isAdmin);
  return isAdmin();
};

/**
 * Custom hook for user information
 */
export const useUser = () => {
  return useAuthStore((state) => state.user);
};

/**
 * Custom hook for auth status
 */
export const useIsAuthenticated = () => {
  return useAuthStore((state) => state.isAuthenticated);
};
