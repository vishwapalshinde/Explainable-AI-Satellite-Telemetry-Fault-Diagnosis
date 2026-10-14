'use client'

import { 
  LayoutDashboard, 
  Satellite, 
  Activity, 
  AlertTriangle, 
  Brain,
  Database,
  Settings,
  Radio
} from 'lucide-react'
import { useTelemetryStore } from '@/store/telemetryStore'
import { useAuthStore } from '@/store/authStore'

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, permission: 'view_telemetry' },
  { id: 'satellites', label: 'Mission Satellite', icon: Satellite, permission: 'view_telemetry' },
  { id: 'telemetry', label: 'Telemetry', icon: Activity, permission: 'view_telemetry' },
  { id: 'diagnosis', label: 'Fault Diagnosis', icon: AlertTriangle, permission: 'diagnose_faults' },
  { id: 'insights', label: 'XAI Insights', icon: Brain, permission: 'diagnose_faults' },
  { id: 'datastore', label: 'Data Store', icon: Database, permission: 'download_data' },
  { id: 'settings', label: 'Settings', icon: Settings, adminOnly: true },
]

export default function Sidebar() {
  const { currentPage, setCurrentPage } = useTelemetryStore()
  const { hasPermission, isAdmin } = useAuthStore()
  const isOnline = true

  const visibleMenuItems = menuItems.filter((item) => {
    if (item.adminOnly) {
      return isAdmin()
    }
    if (item.permission) {
      return hasPermission(item.permission)
    }
    return true
  })
  
  return (
    <aside className="hidden md:flex w-64 shrink-0 bg-[#0a1628] border-r border-cyan-900/30 flex-col">
      {/* Logo Section */}
      <div className="p-6 border-b border-cyan-900/30">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <Radio className="w-8 h-8 text-cyan-400" />
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-wide">SATDIAG</h1>
            <p className="text-xs text-cyan-400 uppercase tracking-wider">XAI Telemetry</p>
          </div>
        </div>
      </div>
      
      {/* Navigation Menu */}
      <nav className="flex-1 p-4 space-y-2">
        {visibleMenuItems.map((item) => {
          const Icon = item.icon
          const isActive = currentPage === item.id
          
          return (
            <button
              key={item.id}
              onClick={() => setCurrentPage(item.id as any)}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                isActive 
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50' 
                  : 'text-gray-400 hover:bg-cyan-500/10 hover:text-cyan-300'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </button>
          )
        })}
      </nav>
      
      {/* System Status Footer */}
      <div className="p-4 border-t border-cyan-900/30">
        <div className="flex items-center space-x-2 text-sm">
          <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
          <span className="text-gray-400">SYSTEM ONLINE</span>
        </div>
      </div>
    </aside>
  )
}
