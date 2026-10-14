'use client'

import { Settings, Save } from 'lucide-react'
import { useState } from 'react'

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    updateInterval: 1000,
    anomalyThreshold: 0.5,
    confidenceThreshold: 0.7,
    darkMode: true,
    autoRefresh: true,
    notificationsEnabled: true,
    dataRetention: 7,
  })

  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    // In production, save to backend
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3 mb-6">
        <Settings className="w-6 h-6 text-cyan-400" />
        <h2 className="text-2xl font-bold text-white">System Settings</h2>
      </div>

      {/* Notification */}
      {saved && (
        <div className="bg-green-500/20 border border-green-500 text-green-100 px-4 py-3 rounded-lg">
          <p className="font-semibold">✓ Settings saved successfully</p>
        </div>
      )}

      {/* Telemetry Settings */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Telemetry Settings</h3>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">Update Interval (ms)</label>
            <input
              type="number"
              value={settings.updateInterval}
              onChange={(e) => setSettings({...settings, updateInterval: parseInt(e.target.value)})}
              className="w-full mt-2 px-3 py-2 bg-[#051020] border border-cyan-900/30 rounded text-cyan-400 focus:outline-none focus:border-cyan-500"
            />
            <p className="text-xs text-gray-600 mt-1">How often to fetch new data (1000ms = 1 second)</p>
          </div>

          <div>
            <label className="text-sm text-gray-400">Auto Refresh</label>
            <div className="flex items-center mt-2">
              <input
                type="checkbox"
                checked={settings.autoRefresh}
                onChange={(e) => setSettings({...settings, autoRefresh: e.target.checked})}
                className="w-4 h-4"
              />
              <span className="text-sm text-gray-400 ml-2">Enable automatic data refresh</span>
            </div>
          </div>
        </div>
      </div>

      {/* Anomaly Detection Settings */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Anomaly Detection</h3>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">Anomaly Score Threshold</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.anomalyThreshold}
              onChange={(e) => setSettings({...settings, anomalyThreshold: parseFloat(e.target.value)})}
              className="w-full mt-2"
            />
            <p className="text-sm text-cyan-400 font-mono mt-1">{settings.anomalyThreshold.toFixed(1)}</p>
            <p className="text-xs text-gray-600 mt-1">Values above this trigger anomaly alert</p>
          </div>

          <div>
            <label className="text-sm text-gray-400">Confidence Threshold</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.confidenceThreshold}
              onChange={(e) => setSettings({...settings, confidenceThreshold: parseFloat(e.target.value)})}
              className="w-full mt-2"
            />
            <p className="text-sm text-cyan-400 font-mono mt-1">{settings.confidenceThreshold.toFixed(1)}</p>
            <p className="text-xs text-gray-600 mt-1">Minimum confidence for predictions</p>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Notifications</h3>
        <div className="space-y-3">
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={settings.notificationsEnabled}
              onChange={(e) => setSettings({...settings, notificationsEnabled: e.target.checked})}
              className="w-4 h-4"
            />
            <span className="text-sm text-gray-400 ml-2">Enable notifications</span>
          </div>
        </div>
      </div>

      {/* Data Management */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Data Management</h3>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">Data Retention (days)</label>
            <input
              type="number"
              value={settings.dataRetention}
              onChange={(e) => setSettings({...settings, dataRetention: parseInt(e.target.value)})}
              className="w-full mt-2 px-3 py-2 bg-[#051020] border border-cyan-900/30 rounded text-cyan-400 focus:outline-none focus:border-cyan-500"
            />
            <p className="text-xs text-gray-600 mt-1">Keep telemetry data for this many days before deletion</p>
          </div>

          <div className="pt-4 border-t border-cyan-900/20">
            <button className="px-4 py-2 bg-red-900/30 border border-red-500/50 text-red-400 rounded hover:bg-red-900/50 transition">
              Clear Cache
            </button>
            <p className="text-xs text-gray-600 mt-2">Remove cached data and logs</p>
          </div>
        </div>
      </div>

      {/* System Information */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">System Information</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between p-2 bg-[#051020] rounded">
            <span className="text-gray-400">Frontend Version</span>
            <span className="text-cyan-400">1.0.0</span>
          </div>
          <div className="flex justify-between p-2 bg-[#051020] rounded">
            <span className="text-gray-400">Backend API</span>
            <span className="text-cyan-400">http://localhost:8000</span>
          </div>
          <div className="flex justify-between p-2 bg-[#051020] rounded">
            <span className="text-gray-400">Framework</span>
            <span className="text-cyan-400">Next.js 14 + React 18</span>
          </div>
          <div className="flex justify-between p-2 bg-[#051020] rounded">
            <span className="text-gray-400">ML Backend</span>
            <span className="text-cyan-400">FastAPI + PyTorch</span>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="flex items-center space-x-2 px-6 py-3 bg-cyan-500/20 border border-cyan-500/50 rounded-lg text-cyan-400 hover:bg-cyan-500/30 transition-all font-medium"
        >
          <Save className="w-4 h-4" />
          <span>Save Settings</span>
        </button>
      </div>
    </div>
  )
}
