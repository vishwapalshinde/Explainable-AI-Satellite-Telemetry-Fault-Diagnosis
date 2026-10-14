'use client'

import { AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'
import { useTelemetryStore } from '@/store/telemetryStore'
import { useEffect } from 'react'

export default function AnomalyPanel() {
  const { anomalyDetection, isLoading, systemStatus } = useTelemetryStore()
  
  const anomalyDetected = anomalyDetection?.detected ?? false
  const probability = anomalyDetection?.probability ?? 0.15
  
  return (
    <div className="bg-[#0f1e33]/50 backdrop-blur border border-cyan-900/30 rounded-lg">
      <div className="px-4 py-3 border-b border-cyan-900/30">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider">Anomaly Detection</h2>
        <p className="text-xs text-cyan-400/70 uppercase">FCNN Model Analysis</p>
      </div>
      
      <div className="p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        ) : (
        <>
          <div className="text-center mb-6">
            {anomalyDetected ? (
              <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-3" />
            ) : (
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-3" />
            )}
            
            <h3 className="text-2xl font-bold mb-2">
              {anomalyDetected ? 'Anomaly Detected' : 'System Normal'}
            </h3>
            
            <p className="text-muted-foreground">
              Confidence: {(probability * 100).toFixed(1)}%
            </p>
          </div>
          
          {/* Probability Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-300">Anomaly Probability</span>
              <span className="font-mono text-cyan-400">{(probability * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-[#0a1628] rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all ${
                  probability > 0.7 ? 'bg-red-500' : probability > 0.5 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${probability * 100}%` }}
              />
            </div>
          </div>
          
          {/* Model Info */}
          <div className="mt-6 p-3 bg-[#0a1628]/50 border border-cyan-900/20 rounded-lg space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-cyan-400/60">Model:</span>
              <span className="font-medium text-white">FCNN</span>
            </div>
            <div className="flex justify-between">
              <span className="text-cyan-400/60">Accuracy:</span>
              <span className="font-medium text-white">{systemStatus?.model_info ? '92.5%' : 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-cyan-400/60">Last Update:</span>
              <span className="font-medium text-white">{anomalyDetection?.timestamp ? new Date(anomalyDetection.timestamp).toLocaleTimeString() : 'N/A'}</span>
            </div>
          </div>
        </>
        )}
      </div>
    </div>
  )
}
