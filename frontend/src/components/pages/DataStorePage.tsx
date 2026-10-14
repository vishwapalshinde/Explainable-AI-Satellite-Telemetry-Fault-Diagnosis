'use client'

import { Database } from 'lucide-react'

export default function DataStorePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3 mb-6">
        <Database className="w-6 h-6 text-cyan-400" />
        <h2 className="text-2xl font-bold text-white">Data Store & Management</h2>
      </div>

      {/* Dataset Information */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Dataset: ESA OPS-SAT ADCS</h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between p-2 bg-[#051020] rounded">
              <span className="text-gray-400">Mission</span>
              <span className="text-cyan-400">OPS-SAT CubeSat</span>
            </div>
            <div className="flex justify-between p-2 bg-[#051020] rounded">
              <span className="text-gray-400">Subsystem</span>
              <span className="text-cyan-400">ADCS (Attitude Determination)</span>
            </div>
            <div className="flex justify-between p-2 bg-[#051020] rounded">
              <span className="text-gray-400">Total Channels</span>
              <span className="text-cyan-400">9</span>
            </div>
            <div className="flex justify-between p-2 bg-[#051020] rounded">
              <span className="text-gray-400">Magnetometer Channels</span>
              <span className="text-green-400">3 (CADC0872-0874)</span>
            </div>
            <div className="flex justify-between p-2 bg-[#051020] rounded">
              <span className="text-gray-400">Photodiode Channels</span>
              <span className="text-blue-400">6 (CADC0875-0880)</span>
            </div>
          </div>
        </div>

        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Files</h3>
          <div className="space-y-3 text-sm">
            <div className="p-3 bg-[#051020] rounded border border-cyan-900/20">
              <p className="font-semibold text-cyan-400">dataset.csv</p>
              <p className="text-gray-500 text-xs mt-1">2,125 feature segments with labels</p>
              <p className="text-gray-600 text-xs mt-1">Pre-computed features for training</p>
            </div>
            <div className="p-3 bg-[#051020] rounded border border-cyan-900/20">
              <p className="font-semibold text-cyan-400">segments.csv</p>
              <p className="text-gray-500 text-xs mt-1">303,000+ raw time-series readings</p>
              <p className="text-gray-600 text-xs mt-1">High-resolution telemetry data</p>
            </div>
          </div>
        </div>
      </div>

      {/* Channel Details */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Channel Mapping</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Magnetometer */}
          <div className="bg-[#051020] rounded p-4 border border-green-900/30">
            <p className="text-green-400 text-xs font-semibold uppercase mb-3">Magnetometer (CADC0872-0874)</p>
            <div className="space-y-2 text-xs">
              <div>
                <p className="text-gray-400">CADC0872</p>
                <p className="text-cyan-400 font-mono">Magnetic Field X</p>
              </div>
              <div>
                <p className="text-gray-400">CADC0873</p>
                <p className="text-cyan-400 font-mono">Magnetic Field Y</p>
              </div>
              <div>
                <p className="text-gray-400">CADC0874</p>
                <p className="text-cyan-400 font-mono">Magnetic Field Z</p>
              </div>
            </div>
          </div>

          {/* Photodiodes */}
          <div className="bg-[#051020] rounded p-4 border border-blue-900/30">
            <p className="text-blue-400 text-xs font-semibold uppercase mb-3">Photodiodes (CADC0875-0880)</p>
            <div className="space-y-1 text-xs">
              <p className="text-cyan-400 font-mono">CADC0875 - Sun Sensor 1</p>
              <p className="text-cyan-400 font-mono">CADC0876 - Sun Sensor 2</p>
              <p className="text-cyan-400 font-mono">CADC0877 - Sun Sensor 3</p>
              <p className="text-cyan-400 font-mono">CADC0878 - Sun Sensor 4</p>
              <p className="text-cyan-400 font-mono">CADC0879 - Sun Sensor 5</p>
              <p className="text-cyan-400 font-mono">CADC0880 - Sun Sensor 6</p>
            </div>
          </div>

          {/* Storage Info */}
          <div className="bg-[#051020] rounded p-4 border border-yellow-900/30">
            <p className="text-yellow-400 text-xs font-semibold uppercase mb-3">Storage</p>
            <div className="space-y-2 text-xs">
              <div>
                <p className="text-gray-400">Location</p>
                <p className="text-cyan-400">dataset/</p>
              </div>
              <div>
                <p className="text-gray-400">Format</p>
                <p className="text-cyan-400">CSV (Pandas-compatible)</p>
              </div>
              <div>
                <p className="text-gray-400">Size</p>
                <p className="text-cyan-400">~100MB total</p>
              </div>
              <div>
                <p className="text-gray-400">Records</p>
                <p className="text-cyan-400">303K+ readings</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Database Statistics */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Database Statistics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-[#051020] rounded p-4 border border-cyan-900/20">
            <p className="text-gray-400 text-xs">Features Extracted</p>
            <p className="text-2xl font-bold text-cyan-400 mt-2">2,125</p>
            <p className="text-xs text-gray-600 mt-1">samples in training set</p>
          </div>
          <div className="bg-[#051020] rounded p-4 border border-cyan-900/20">
            <p className="text-gray-400 text-xs">Time-Series Records</p>
            <p className="text-2xl font-bold text-cyan-400 mt-2">303K+</p>
            <p className="text-xs text-gray-600 mt-1">raw readings</p>
          </div>
          <div className="bg-[#051020] rounded p-4 border border-cyan-900/20">
            <p className="text-gray-400 text-xs">Training/Test Split</p>
            <p className="text-2xl font-bold text-cyan-400 mt-2">80/20</p>
            <p className="text-xs text-gray-600 mt-1">1,700 / 425 samples</p>
          </div>
          <div className="bg-[#051020] rounded p-4 border border-cyan-900/20">
            <p className="text-gray-400 text-xs">Features per Sample</p>
            <p className="text-2xl font-bold text-cyan-400 mt-2">9</p>
            <p className="text-xs text-gray-600 mt-1">channel values</p>
          </div>
        </div>
      </div>

      {/* Anomaly Distribution */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Anomaly Distribution in Dataset</h3>
        <div className="space-y-3">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-gray-400">Normal Samples</span>
              <span className="text-sm text-green-400 font-semibold">1,955 (92%)</span>
            </div>
            <div className="w-full bg-[#051020] rounded h-2 overflow-hidden">
              <div className="w-[92%] h-full bg-green-500/50"></div>
            </div>
          </div>
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-gray-400">Anomalous Samples</span>
              <span className="text-sm text-red-400 font-semibold">170 (8%)</span>
            </div>
            <div className="w-full bg-[#051020] rounded h-2 overflow-hidden">
              <div className="w-[8%] h-full bg-red-500/50"></div>
            </div>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-4">Balanced dataset ensures model learns both normal and anomalous patterns effectively</p>
      </div>
    </div>
  )
}
