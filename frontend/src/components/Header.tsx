'use client'

import { Satellite, Activity, AlertTriangle } from 'lucide-react'
import { useTelemetryStore } from '@/store/telemetryStore'

export default function Header() {
  const { isConnected, systemStatus } = useTelemetryStore()
  
  return (
    <header className="border-b border-border bg-card">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <div className="bg-primary/20 p-2 rounded-lg">
              <Satellite className="w-8 h-8 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Satellite Telemetry Fault Diagnosis
              </h1>
              <p className="text-sm text-muted-foreground">
                ESA OPS-SAT ADCS Subsystem
              </p>
            </div>
          </div>
          
          {/* Status Indicators */}
          <div className="flex items-center space-x-4">
            
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-sm font-medium">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            
            {/* System Health */}
            {systemStatus && (
              <div className="flex items-center space-x-2 px-3 py-2 bg-secondary rounded-lg">
                <Activity className="w-4 h-4 text-green-500" />
                <span className="text-sm font-medium">
                  System Operational
                </span>
              </div>
            )}
            
          </div>
          
        </div>
      </div>
    </header>
  )
}
