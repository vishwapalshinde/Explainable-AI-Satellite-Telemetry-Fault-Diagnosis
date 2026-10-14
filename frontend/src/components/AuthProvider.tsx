'use client';

import { useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

/**
 * Protected routes that require authentication
 */
const PROTECTED_ROUTES = [
  '/',
  '/dashboard',
  '/telemetry',
  '/diagnosis',
  '/settings',
];

/**
 * Public routes that don't require authentication
 */
const PUBLIC_ROUTES = [
  '/login',
];

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * AuthProvider Component
 * 
 * Provides authentication context to the app:
 * - Initializes auth state from localStorage
 * - Protects routes (redirects to login if not authenticated)
 * - Provides Zustand store to all components
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, initializeFromStorage } = useAuthStore();

  useEffect(() => {
    // Initialize auth from localStorage
    initializeFromStorage();
  }, [initializeFromStorage]);

  useEffect(() => {
    // Route protection logic
    if (typeof window === 'undefined') return;

    const isPublicRoute = PUBLIC_ROUTES.includes(pathname);
    const isProtectedRoute = PROTECTED_ROUTES.includes(pathname);

    // If on login page and already authenticated, redirect to dashboard
    if (isPublicRoute && isAuthenticated && pathname === '/login') {
      router.push('/');
      return;
    }

    // If on protected route and not authenticated, redirect to login
    if (isProtectedRoute && !isAuthenticated) {
      router.push('/login');
      return;
    }
  }, [isAuthenticated, pathname, router]);

  return <>{children}</>;
}
