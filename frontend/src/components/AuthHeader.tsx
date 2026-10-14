'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useTelemetryStore } from '@/store/telemetryStore';
import apiClient from '@/lib/api';
import { LogOut, User, Settings, Menu, X } from 'lucide-react';

interface HeaderProps {
  title?: string;
}

/**
 * Header Component
 * 
 * Displays:
 * - App title
 * - User profile with role badge
 * - User menu (profile, settings, logout)
 */
export function Header({ title = 'Satellite Diagnosis Dashboard' }: HeaderProps) {
  const router = useRouter();
  const { user, logout, isAdmin } = useAuthStore();
  const { setCurrentPage } = useTelemetryStore();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleSettings = () => {
    setCurrentPage('settings');
    setMenuOpen(false);
  };

  const handleLogout = async () => {
    try {
      // Call logout endpoint (optional, for server-side cleanup)
      await apiClient.post('/api/v1/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local auth state
      logout();
      // Redirect to login
      router.push('/login');
    }
  };

  if (!user) {
    return null;
  }

  return (
    <header className="sticky top-0 z-40 bg-slate-800 border-b border-slate-700 shadow-lg">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">S</span>
            </div>
            <div className="text-left">
              <h1 className="text-lg sm:text-xl font-semibold text-white leading-tight">{title}</h1>
              <p className="text-xs text-slate-400 tracking-wide">Enterprise Anomaly Detection</p>
            </div>
          </div>

          {/* User Menu - Desktop */}
          <div className="hidden md:flex items-center gap-6">
            {/* Role Badge */}
            <div className="flex items-center gap-2 px-3 py-1 bg-slate-700 rounded-lg">
              <span className="text-sm text-slate-300">Role:</span>
              <span className={`text-sm font-semibold px-2 py-0.5 rounded ${
                isAdmin() ? 'bg-red-900 text-red-200' : 'bg-blue-900 text-blue-200'
              }`}>
                {user.role}
              </span>
            </div>

            {/* User Info */}
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-slate-300" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">{user.username}</p>
                <p className="text-xs text-slate-400">{user.email}</p>
              </div>
            </div>

            {/* Settings Button */}
            <button
              onClick={handleSettings}
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition"
              title="Open settings"
            >
              <Settings className="w-5 h-5" />
            </button>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 bg-red-900 hover:bg-red-800 text-red-100 rounded-lg transition font-medium text-sm"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 text-slate-400 hover:text-white"
          >
            {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {menuOpen && (
          <div className="md:hidden pb-4 border-t border-slate-700 space-y-2">
            <div className="flex items-center gap-2 px-2 py-2 bg-slate-700 rounded">
              <User className="w-4 h-4 text-slate-400" />
              <div>
                <p className="text-sm font-medium text-white">{user.username}</p>
                <p className="text-xs text-slate-400">{user.email}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 px-2 py-1">
              <span className="text-xs text-slate-400">Role:</span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                isAdmin() ? 'bg-red-900 text-red-200' : 'bg-blue-900 text-blue-200'
              }`}>
                {user.role}
              </span>
            </div>

            <button
              onClick={handleSettings}
              className="w-full flex items-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-100 rounded transition font-medium text-sm"
            >
              <Settings className="w-4 h-4" />
              Settings
            </button>

            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-3 py-2 bg-red-900 hover:bg-red-800 text-red-100 rounded transition font-medium text-sm"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
