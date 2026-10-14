'use client'

import { Activity } from 'lucide-react'
import TelemetryPanel from '@/components/TelemetryPanel'
import TelemetryChart from '@/components/TelemetryChart'
import { useTelemetryStore } from '@/store/telemetryStore'

export default function TelemetryPage() {
  const { telemetryData, currentFeatures } = useTelemetryStore()

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3 mb-6">
        <Activity className="w-6 h-6 text-cyan-400" />
        <h2 className="text-2xl font-bold text-white">Live Telemetry Ingestion</h2>
      </div>

      {/* Live Channels */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">ADCS Telemetry Channels (Real-time from segments.csv)</h3>
        <TelemetryPanel />
        <div className="mt-4 text-xs text-gray-500">
          <p>Data source: ESA OPS-SAT raw segments (segments.csv)</p>
          <p>Update rate: every 5 seconds (near real-time playback)</p>
          <p>Active channels: CADC0872-CADC0880 (magnetometer + photodiode ADCS channels)</p>
          <p>Primary anomaly channels: CADC0872, CADC0873, CADC0874 (3-axis magnetometer)</p>
        </div>
      </div>

      {/* Telemetry Chart - Historical Trend */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Channel History (Last 60 seconds)</h3>
        <TelemetryChart />
      </div>

      {/* Feature Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Current Features (Extracted)</h3>
          <div className="space-y-3 text-sm">
            {Object.entries(currentFeatures).length > 0 ? (
              (() => {
                const primary = currentFeatures['CADC0872'] || Object.values(currentFeatures)[0]
                const primaryRecord = primary as unknown as Record<string, number>
                return primary ? Object.entries(primaryRecord).map(([key, value]: any) => (
                  <div key={key} className="flex justify-between items-center pb-2 border-b border-cyan-900/20">
                    <span className="text-gray-400">{key}</span>
                    <span className="text-cyan-400 font-mono">{Number.isFinite(value) ? value.toFixed(6) : 'N/A'}</span>
                  </div>
                )) : <p className="text-gray-500">No features extracted yet. Waiting for telemetry snapshot.</p>
              })()
            ) : (
              <p className="text-gray-500">No features extracted yet. Inject telemetry data.</p>
            )}
          </div>
        </div>

        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Data Statistics</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400">Total Samples</span>
              <span className="text-cyan-400">{telemetryData.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Anomalies Found</span>
              <span className="text-red-400">{telemetryData.filter(d => d.anomaly).length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Normal Readings</span>
              <span className="text-green-400">{telemetryData.filter(d => !d.anomaly).length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Anomaly Rate</span>
              <span className="text-yellow-400">
                {telemetryData.length > 0 
                  ? ((telemetryData.filter(d => d.anomaly).length / telemetryData.length) * 100).toFixed(2)
                  : '0'}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Raw Data Table */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Recent Telemetry Readings</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-cyan-900/30">
                <th className="text-left py-2 px-3 text-cyan-400">Timestamp</th>
                <th className="text-left py-2 px-3 text-cyan-400">Channel</th>
                <th className="text-right py-2 px-3 text-cyan-400">Value</th>
                <th className="text-center py-2 px-3 text-cyan-400">Status</th>
              </tr>
            </thead>
            <tbody>
              {telemetryData.slice(-10).reverse().map((data, idx) => (
                <tr key={idx} className="border-b border-cyan-900/10 hover:bg-cyan-900/10">
                  <td className="py-2 px-3 text-gray-400">{new Date(data.timestamp).toLocaleTimeString()}</td>
                  <td className="py-2 px-3 text-cyan-300">{data.channel}</td>
                  <td className="py-2 px-3 text-right font-mono text-white">{data.value.toFixed(4)}</td>
                  <td className="py-2 px-3 text-center">
                    {data.anomaly ? (
                      <span className="px-2 py-1 bg-red-900/30 text-red-400 rounded text-xs">ANOMALY</span>
                    ) : (
                      <span className="px-2 py-1 bg-green-900/30 text-green-400 rounded text-xs">NORMAL</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
