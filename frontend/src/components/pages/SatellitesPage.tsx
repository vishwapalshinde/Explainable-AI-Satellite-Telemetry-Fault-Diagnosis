'use client'

import { Satellite } from 'lucide-react'
import SatelliteList from '@/components/SatelliteList'

export default function SatellitesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3 mb-6">
        <Satellite className="w-6 h-6 text-cyan-400" />
        <h2 className="text-2xl font-bold text-white">ESA CubeSat Mission Status</h2>
      </div>

      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Spacecraft Status</h3>
        <SatelliteList />
      </div>

      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">ADCS Monitoring Scope</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-300">
          <div className="bg-[#051020] rounded p-4 border border-cyan-900/20">
            <p className="text-cyan-400 font-semibold mb-2">Magnetometer Channels</p>
            <p>CADC0872, CADC0873, CADC0874 are used for anomaly detection and RCA context.</p>
          </div>
          <div className="bg-[#051020] rounded p-4 border border-cyan-900/20">
            <p className="text-cyan-400 font-semibold mb-2">Photodiode Channels</p>
            <p>CADC0875 to CADC0880 complement ADCS root-cause reasoning and cross-channel evidence.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
