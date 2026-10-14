'use client'

import { Network, Loader2 } from 'lucide-react'
import { useTelemetryStore } from '@/store/telemetryStore'
import { useEffect } from 'react'

export default function KnowledgeGraphPanel() {
  const { rootCauses, kgStats, isLoading, fetchKnowledgeGraphStats } = useTelemetryStore()
  
  useEffect(() => {
    fetchKnowledgeGraphStats()
  }, [fetchKnowledgeGraphStats])
  
  return (
    <div className="bg-[#0f1e33]/50 backdrop-blur border border-cyan-900/30 rounded-lg">
      <div className="px-4 py-3 border-b border-cyan-900/30">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider">Root Cause Analysis</h2>
        <p className="text-xs text-cyan-400/70 uppercase">Knowledge Graph Reasoning</p>
      </div>
      
      <div className="p-6">
        <div className="flex items-center justify-center mb-6">
          <Network className="w-12 h-12 text-primary" />
        </div>
        
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        ) : (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase">
            Probable Root Causes
          </h3>
          
          {(!rootCauses || rootCauses.length === 0) ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No anomalies detected. System operating normally.
            </p>
          ) : (
            rootCauses.map((cause, idx) => (
            <div key={idx} className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="font-medium">{cause.fault}</span>
                <span className="text-muted-foreground">
                  {(cause.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2">
                <div 
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{ width: `${cause.confidence * 100}%` }}
                />
              </div>
            </div>
          ))
          )}
        </div>
        )
        }
        
        {/* Graph Stats */}
        <div className="mt-6 p-3 bg-[#0a1628]/50 border border-cyan-900/20 rounded-lg space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-cyan-400/60">Nodes:</span>
            <span className="font-medium text-white">{kgStats?.nodes ?? 24}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-cyan-400/60">Relationships:</span>
            <span className="font-medium text-white">{kgStats?.relationships ?? 42}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-cyan-400/60">Affected Subsystems:</span>
            <span className="font-medium text-white">ADCS, Magnetometer</span>
          </div>
        </div>
      </div>
    </div>
  )
}
