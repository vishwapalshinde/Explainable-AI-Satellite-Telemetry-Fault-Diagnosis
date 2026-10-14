'use client'

interface StatsCardProps {
  title: string
  value: string | number
  subtitle: string
  detail?: string
  icon: React.ReactNode
  iconColor?: string
  trend?: string
}

export default function StatsCard({ 
  title, 
  value, 
  subtitle, 
  detail, 
  icon, 
  iconColor = 'text-cyan-400',
  trend 
}: StatsCardProps) {
  return (
    <div className="bg-[#0f1e33]/50 backdrop-blur border border-cyan-900/30 rounded-lg p-4 hover:border-cyan-500/50 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-xs text-cyan-400/70 uppercase tracking-wider mb-1">{title}</p>
          <h3 className="text-3xl font-bold text-white">{value}</h3>
        </div>
        <div className={`${iconColor} p-2 bg-cyan-500/10 rounded-lg`}>
          {icon}
        </div>
      </div>
      
      <p className="text-sm text-gray-400">{subtitle}</p>
      
      {detail && (
        <div className="mt-2 pt-2 border-t border-cyan-900/30">
          <p className="text-xs text-cyan-400/60">{detail}</p>
        </div>
      )}
      
      {trend && (
        <div className="mt-2 pt-2 border-t border-cyan-900/30">
          <p className="text-xs text-green-400">{trend}</p>
        </div>
      )}
    </div>
  )
}
