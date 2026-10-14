'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

type AuthMode = 'signin' | 'signup';

export default function LoginPage() {
  const [mode, setMode] = useState<AuthMode>('signin');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const router = useRouter();
  const { setUser, setTokens } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const normalizedUsername = username.trim();
    const normalizedEmail = email.trim().toLowerCase();

    if (mode === 'signup' && password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (!normalizedUsername) {
      setError('Username is required.');
      return;
    }

    setLoading(true);

    try {
      if (mode === 'signup') {
        await apiClient.post('/api/v1/auth/register', {
          username: normalizedUsername,
          email: normalizedEmail,
          password,
        });

        // Automatically sign in immediately after registration to verify persistence.
        const loginResponse = await apiClient.post('/api/v1/auth/login', {
          username: normalizedUsername,
          password,
        });

        const loginData = loginResponse.data;
        setTokens(loginData.access_token, loginData.refresh_token);
        setUser(loginData.user);
        router.push('/');
      } else {
        const response = await apiClient.post('/api/v1/auth/login', {
          username: normalizedUsername,
          password,
        });

        const data = response.data;
        setTokens(data.access_token, data.refresh_token);
        setUser(data.user);
        router.push('/');
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (!err?.response) {
        setError('Failed to fetch. Check backend server and CORS settings (localhost vs 127.0.0.1).');
      } else {
        setError(detail || (mode === 'signup' ? 'Sign up failed' : 'Sign in failed'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Satellite Diagnosis</h1>
          <p className="text-slate-400">Enterprise Anomaly Detection System</p>
        </div>

        {/* Auth Form */}
        <div className="bg-slate-800 rounded-lg shadow-xl p-8">
          <div className="mb-6 grid grid-cols-2 gap-2 rounded-lg bg-slate-700 p-1">
            <button
              type="button"
              onClick={() => {
                setMode('signin');
                setError(null);
                setSuccess(null);
              }}
              className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
                mode === 'signin' ? 'bg-blue-600 text-white' : 'text-slate-200 hover:bg-slate-600'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('signup');
                setError(null);
                setSuccess(null);
              }}
              className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
                mode === 'signup' ? 'bg-blue-600 text-white' : 'text-slate-200 hover:bg-slate-600'
              }`}
            >
              Sign Up
            </button>
          </div>

          <h2 className="text-2xl font-bold text-white mb-6">{mode === 'signin' ? 'Sign In' : 'Create Account'}</h2>

          {error && (
            <div className="mb-4 p-4 bg-red-900 border border-red-700 rounded-lg">
              <p className="text-red-200 text-sm">{error}</p>
            </div>
          )}

          {success && (
            <div className="mb-4 p-4 bg-emerald-900 border border-emerald-700 rounded-lg">
              <p className="text-emerald-200 text-sm">{success}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username Field */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-slate-200 mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
                disabled={loading}
                required
              />
            </div>

            {mode === 'signup' && (
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-200 mb-2">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
                  disabled={loading}
                  required
                />
              </div>
            )}

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-200 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
                disabled={loading}
                required
              />
            </div>

            {mode === 'signup' && (
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-200 mb-2">
                  Confirm Password
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter your password"
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
                  disabled={loading}
                  required
                />
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-6 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-semibold rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-blue-300 border-t-white rounded-full animate-spin" />
                  {mode === 'signin' ? 'Signing in...' : 'Creating account...'}
                </>
              ) : (
                mode === 'signin' ? 'Sign In' : 'Sign Up'
              )}
            </button>
          </form>

          {/* Sign In Help */}
          <div className="mt-6 p-4 bg-slate-700 border border-slate-600 rounded-lg">
            <p className="text-xs text-slate-400 mb-2 font-semibold">Testing Roles:</p>
            <p className="text-xs text-slate-300">Use Sign Up to create a viewer account.</p>
            <p className="text-xs text-slate-300">Create admin/engineer users from backend scripts or DB role assignment.</p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-slate-500 text-sm mt-6">
          © 2026 Satellite Diagnosis System. All rights reserved.
        </p>
      </div>
    </div>
  );
}
