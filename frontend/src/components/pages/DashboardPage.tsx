'use client'

import { Satellite, Radio, AlertTriangle, Thermometer } from 'lucide-react'
import StatsCard from '@/components/StatsCard'
import TelemetryPanel from '@/components/TelemetryPanel'
import AnomalyPanel from '@/components/AnomalyPanel'
import KnowledgeGraphPanel from '@/components/KnowledgeGraphPanel'
import DiagnosisPanel from '@/components/DiagnosisPanel'
import { useTelemetryStore } from '@/store/telemetryStore'

export default function DashboardPage() {
  const { anomalyDetection, isConnected } = useTelemetryStore()
  const healthScore = Math.max(0, Math.min(100, (1 - (anomalyDetection?.probability ?? 0)) * 100))

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Mission Spacecraft"
          value="1/1"
          subtitle="ESA CubeSat telemetry online"
          detail="ADCS stream available"
          icon={<Satellite className="w-6 h-6" />}
          iconColor="text-green-400"
        />
        
        <StatsCard
          title="Signal Strength"
          value="ADCS Link"
          subtitle="Single-satellite telemetry stream"
          detail="Dataset-driven near real-time playback"
          icon={<Radio className="w-6 h-6" />}
          iconColor="text-cyan-400"
        />
        
        <StatsCard
          title="Active Faults"
          value={anomalyDetection?.detected ? "1" : "0"}
          subtitle={anomalyDetection?.detected ? `Severity ${anomalyDetection?.severity ?? 'HIGH'}` : "All systems nominal"}
          detail={anomalyDetection?.detected ? "Live anomaly from replay stream" : "No anomaly above threshold"}
          icon={<AlertTriangle className="w-6 h-6" />}
          iconColor={anomalyDetection?.detected ? "text-red-400" : "text-green-400"}
        />
        
        <StatsCard
          title="System Health"
          value={`${healthScore.toFixed(1)}%`}
          subtitle={isConnected ? "Model-linked operational score" : "Backend disconnected"}
          detail={isConnected ? "Derived from current anomaly probability" : "Check API connectivity"}
          icon={<Thermometer className="w-6 h-6" />}
          iconColor="text-yellow-400"
        />
      </div>
      
      {/* Main Grid */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Live ADCS Telemetry</h3>
        <TelemetryPanel />
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Anomaly Detection</h3>
          <AnomalyPanel />
        </div>
        
        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Root Cause Analysis</h3>
          <KnowledgeGraphPanel />
        </div>
      </div>
      
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">XAI Diagnosis & Recommendations</h3>
        <DiagnosisPanel />
      </div>
    </div>
  )
}
