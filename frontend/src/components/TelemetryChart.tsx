'use client'

import { useEffect, useRef, useState } from 'react'
import { Activity } from 'lucide-react'
import { useTelemetryStore } from '@/store/telemetryStore'

export default function TelemetryChart() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { telemetryData } = useTelemetryStore()
  const [dataPoints, setDataPoints] = useState<number[]>(Array(100).fill(0))
  const [seriesLabel, setSeriesLabel] = useState('CADC0872')
  
  useEffect(() => {
    const targetChannel = 'CADC0872'
    const channelData = telemetryData
      .filter((d) => d.channel === targetChannel)
      .slice(-100)
      .map((d) => Number(d.value))

    if (channelData.length === 0) {
      setDataPoints(Array(100).fill(0))
      return
    }

    const min = Math.min(...channelData)
    const max = Math.max(...channelData)
    const span = max - min || 1
    const normalized = channelData.map((v) => ((v - min) / span) * 100)
    const padded = [...Array(Math.max(0, 100 - normalized.length)).fill(normalized[0] ?? 0), ...normalized]

    setSeriesLabel(targetChannel)
    setDataPoints(padded)
  }, [telemetryData])
  
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    // Draw grid
    ctx.strokeStyle = 'rgba(6, 182, 212, 0.1)'
    ctx.lineWidth = 1
    
    // Horizontal lines
    for (let i = 0; i <= 4; i++) {
      const y = (canvas.height / 4) * i
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(canvas.width, y)
      ctx.stroke()
    }
    
    // Draw signal line
    ctx.strokeStyle = '#06b6d4'
    ctx.lineWidth = 2
    ctx.shadowBlur = 8
    ctx.shadowColor = '#06b6d4'
    
    ctx.beginPath()
    dataPoints.forEach((value, index) => {
      const x = (canvas.width / dataPoints.length) * index
      const y = canvas.height - ((value / 100) * canvas.height)
      
      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()
    
    // Draw area fill
    ctx.lineTo(canvas.width, canvas.height)
    ctx.lineTo(0, canvas.height)
    ctx.closePath()
    ctx.fillStyle = 'rgba(6, 182, 212, 0.1)'
    ctx.fill()
    
  }, [dataPoints])
  
  return (
    <div className="bg-[#0f1e33]/50 backdrop-blur border border-cyan-900/30 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-cyan-900/30 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">Telemetry Stream</h2>
          <p className="text-xs text-cyan-400/70 uppercase">Live Dataset Trend ({seriesLabel})</p>
        </div>
        
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-cyan-400" />
            <span className="text-cyan-400">LIVE SIGNAL</span>
          </div>
        </div>
      </div>
      
      <div className="relative p-6" style={{ height: '280px' }}>
        <canvas 
          ref={canvasRef} 
          width={800} 
          height={220}
          className="w-full h-full"
        />
        
        {/* Y-axis labels */}
        <div className="absolute left-2 top-6 bottom-6 flex flex-col justify-between text-xs text-cyan-400/50 font-mono">
          <span>100</span>
          <span>75</span>
          <span>50</span>
          <span>25</span>
          <span>0</span>
        </div>
        
        {/* X-axis time labels */}
        <div className="absolute left-12 right-6 bottom-2 flex justify-between text-xs text-cyan-400/50 font-mono">
          <span>T-20m</span>
          <span>T-15m</span>
          <span>T-10m</span>
          <span>T-5m</span>
          <span>T-0m</span>
        </div>
      </div>
    </div>
  )
}
