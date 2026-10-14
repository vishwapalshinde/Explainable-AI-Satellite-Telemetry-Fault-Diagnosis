'use client'

import { Activity, Zap } from 'lucide-react'
import { useTelemetryStore } from '@/store/telemetryStore'
import { useEffect, useState } from 'react'

export default function TelemetryPanel() {
  const { 
    telemetryData, 
    generateAndProcessTelemetry, 
    currentChannels,
    isProcessing,
    lastProcessingTime 
  } = useTelemetryStore()
  const [displayData, setDisplayData] = useState<any[]>([])
  const [autoProcess, setAutoProcess] = useState(true)

  const channelNames: Record<string, { name: string; unit: string }> = {
    CADC0872: { name: 'Magnetometer X', unit: 'T' },
    CADC0873: { name: 'Magnetometer Y', unit: 'T' },
    CADC0874: { name: 'Magnetometer Z', unit: 'T' },
    CADC0875: { name: 'Photodiode 1', unit: 'V' },
    CADC0876: { name: 'Photodiode 2', unit: 'V' },
    CADC0877: { name: 'Photodiode 3', unit: 'V' },
    CADC0878: { name: 'Photodiode 4', unit: 'V' },
    CADC0879: { name: 'Photodiode 5', unit: 'V' },
    CADC0880: { name: 'Photodiode 6', unit: 'V' }
  }
  
  useEffect(() => {
    // Real-time AI processing every 5 seconds
    if (!autoProcess) return
    
    const interval = setInterval(() => {
      generateAndProcessTelemetry()
    }, 5000)
    
    // Initial processing
    generateAndProcessTelemetry()
    
    return () => clearInterval(interval)
  }, [generateAndProcessTelemetry, autoProcess])
  
  useEffect(() => {
    // Update display with latest telemetry for each channel
    const latest = currentChannels.map((channelId) => {
      const channelMeta = channelNames[channelId] || { name: channelId, unit: 'T' }
      const channelData = telemetryData.filter(d => d.channel === channelId)
      const latestData = channelData[channelData.length - 1]
      
      return {
        id: channelId,
        name: channelMeta.name,
        unit: channelMeta.unit,
        value: latestData?.value ?? -2.1e-5,
        status: latestData?.anomaly ? 'anomaly' : 'normal',
        timestamp: latestData?.timestamp
      }
    })
    
    setDisplayData(latest)
  }, [telemetryData, currentChannels])
  
  const channels = displayData
  
  return (
    <div className="bg-[#0f1e33]/50 backdrop-blur border border-cyan-900/30 rounded-lg">
      <div className="px-4 py-3 border-b border-cyan-900/30 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">Live Telemetry</h2>
          <p className="text-xs text-cyan-400/70 uppercase">Real-time AI Processing Active</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setAutoProcess(!autoProcess)}
            className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
              autoProcess 
                ? 'bg-cyan-500/20 border border-cyan-500/50 text-cyan-400' 
                : 'bg-gray-700 text-gray-400'
            }`}
          >
            {autoProcess ? 'AUTO' : 'MANUAL'}
          </button>
          {isProcessing ? (
            <Zap className="w-5 h-5 text-yellow-400 animate-pulse" />
          ) : (
            <Activity className="w-5 h-5 text-cyan-400 animate-pulse" />
          )}
        </div>
      </div>
      
      <div className="p-4 space-y-3">
        {channels.length === 0 ? (
          <div className="p-4 bg-[#0a1628]/40 border border-cyan-900/20 rounded text-sm text-gray-400 text-center">
            Waiting for live replay snapshot from backend...
          </div>
        ) : channels.map((channel) => (
          <div key={channel.id} className="flex items-center justify-between p-3 bg-[#0a1628]/40 border border-cyan-900/20 rounded hover:border-cyan-900/50 transition-colors">
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${channel.status === 'normal' ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
              <span className="font-medium text-white text-sm">{channel.name}</span>
              <span className="text-xs text-cyan-400/60 font-mono">{channel.id}</span>
            </div>
            <div className="text-right">
              <span className="text-lg font-mono text-cyan-400">
                {typeof channel.value === 'number' 
                  ? (channel.unit === 'T' ? channel.value.toExponential(2) : channel.value.toFixed(2))
                  : 'N/A'
                }
              </span>
              <span className="text-xs text-gray-400 ml-1">{channel.unit}</span>
            </div>
          </div>
        ))}
        {lastProcessingTime && (
          <div className="mt-3 pt-3 border-t border-cyan-900/20 text-xs text-cyan-400/60 text-center">
            Last AI Processing: {new Date(lastProcessingTime).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  )
}
