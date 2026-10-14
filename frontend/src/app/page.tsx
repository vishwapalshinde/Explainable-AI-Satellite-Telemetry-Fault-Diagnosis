'use client'

import { useEffect, useState } from 'react'
import { Radio } from 'lucide-react'
import { Header } from '@/components/AuthHeader'
import Sidebar from '@/components/Sidebar'
import DashboardPage from '@/components/pages/DashboardPage'
import SatellitesPage from '@/components/pages/SatellitesPage'
import TelemetryPage from '@/components/pages/TelemetryPage'
import DiagnosisPage from '@/components/pages/DiagnosisPage'
import InsightsPage from '@/components/pages/InsightsPage'
import DataStorePage from '@/components/pages/DataStorePage'
import SettingsPage from '@/components/pages/SettingsPage'
import { useTelemetryStore } from '@/store/telemetryStore'
import { useAuthStore } from '@/store/authStore'

export default function Home() {
  const { fetchSystemStatus, isConnected, error, currentPage } = useTelemetryStore()
  const { hasPermission, isAdmin } = useAuthStore()
  const [mounted, setMounted] = useState(false)

  const canAccessPage = (page: string): boolean => {
    switch (page) {
      case 'dashboard':
      case 'satellites':
      case 'telemetry':
        return hasPermission('view_telemetry')
      case 'diagnosis':
      case 'insights':
        return hasPermission('diagnose_faults')
      case 'datastore':
        return hasPermission('download_data')
      case 'settings':
        return isAdmin()
      default:
        return true
    }
  }

  useEffect(() => {
    setMounted(true)
    
    // Initial fetch
    fetchSystemStatus()
    
    // Poll system status every 10 seconds
    const statusInterval = setInterval(() => {
      fetchSystemStatus()
    }, 10000)
    
    return () => clearInterval(statusInterval)
  }, [fetchSystemStatus])

  const renderPage = () => {
    if (!canAccessPage(currentPage)) {
      return (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-6 text-amber-100">
          <h2 className="text-lg font-semibold">Access Restricted</h2>
          <p className="mt-2 text-sm text-amber-200">
            Your current role does not have permission to view this section.
          </p>
        </div>
      )
    }

    switch(currentPage) {
      case 'dashboard': return <DashboardPage />
      case 'satellites': return <SatellitesPage />
      case 'telemetry': return <TelemetryPage />
      case 'diagnosis': return <DiagnosisPage />
      case 'insights': return <InsightsPage />
      case 'datastore': return <DataStorePage />
      case 'settings': return <SettingsPage />
      default: return <DashboardPage />
    }
  }

  if (!mounted) {
    return null
  }

  return (
    <div className="min-h-screen bg-[#0d1b2a] flex flex-col">
      {/* Header with Auth */}
      <Header />
      
      {/* Sidebar & Main Content */}
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <Sidebar />
        
        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
        
          {/* Connection Status Banner */}
          {!isConnected && (
            <div className="bg-red-500/20 border border-red-500 text-red-100 px-4 py-3 rounded-lg">
              <p className="font-semibold">⚠️ Backend Connection Lost</p>
              <p className="text-sm">{error || 'Attempting to reconnect to API server...'}</p>
            </div>
          )}
          
          {/* Page Content */}
          {renderPage()}
          
        </main>
      </div>
      
      {/* Footer */}
      <footer className="border-t border-cyan-900/30 py-4 bg-[#0a1628]/50 shrink-0">
        <div className="px-6 text-center text-xs text-cyan-400/50">
          <p>Explainable AI-based Satellite Telemetry Fault Diagnosis System</p>
          <p className="mt-1">ESA OPS-SAT ADCS Subsystem Monitoring © 2026</p>
        </div>
      </footer>
    </div>
  )
}
