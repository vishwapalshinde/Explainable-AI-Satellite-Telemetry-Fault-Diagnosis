'use client'

interface SatelliteItemProps {
  name: string
  id: string
  orbit: string
  health: number
  lastUpdate: string
}

function SatelliteItem({ name, id, orbit, health, lastUpdate }: SatelliteItemProps) {
  const healthColor = health >= 95 ? 'text-green-400' : health >= 85 ? 'text-yellow-400' : 'text-red-400'
  const healthBg = health >= 95 ? 'bg-green-500' : health >= 85 ? 'bg-yellow-500' : 'bg-red-500'
  
  return (
    <div className="flex items-center justify-between p-3 bg-[#0a1628]/50 rounded-lg border border-cyan-900/20 hover:border-cyan-500/50 transition-all">
      <div className="flex items-center space-x-3">
        <div className={`w-2 h-2 rounded-full ${healthBg} animate-pulse`} />
        <div>
          <h4 className="text-sm font-semibold text-white">{name}</h4>
          <p className="text-xs text-cyan-400/60">{id} • {orbit}</p>
        </div>
      </div>
      
      <div className="text-right">
        <p className={`text-lg font-bold ${healthColor}`}>{health.toFixed(1)}%</p>
        <p className="text-xs text-gray-500">{lastUpdate}</p>
      </div>
    </div>
  )
}

export default function SatelliteList() {
  const satellites = [
    { name: 'ESA OPS-SAT CubeSat', id: 'OPS-SAT', orbit: 'LEO', health: 98.9, lastUpdate: 'live' },
  ]
  
  return (
    <div className="bg-[#0f1e33]/50 backdrop-blur border border-cyan-900/30 rounded-lg">
      <div className="px-4 py-3 border-b border-cyan-900/30">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider">Mission Spacecraft</h2>
      </div>
      
      <div className="p-4 space-y-3">
        {satellites.map((sat) => (
          <SatelliteItem key={sat.id} {...sat} />
        ))}
      </div>
    </div>
  )
}
