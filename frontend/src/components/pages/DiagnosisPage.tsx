'use client'

import { AlertTriangle, Zap, Loader2 } from 'lucide-react'
import AnomalyPanel from '@/components/AnomalyPanel'
import KnowledgeGraphPanel from '@/components/KnowledgeGraphPanel'
import DiagnosisPanel from '@/components/DiagnosisPanel'
import DiagnosisChatPanel from '@/components/DiagnosisChatPanel'
import { useTelemetryStore } from '@/store/telemetryStore'
import { useState } from 'react'

export default function DiagnosisPage() {
  const { anomalyDetection, rootCauses, diagnosis, forceAnomaly, isLoading, systemStatus, kgStats } = useTelemetryStore()
  const [selectedSeverity, setSelectedSeverity] = useState<'HIGH' | 'MEDIUM' | 'LOW'>('HIGH')
  const ragAvailable = Boolean(systemStatus?.components?.rag_explainer)

  const handleForceAnomaly = async () => {
    await forceAnomaly(selectedSeverity)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <AlertTriangle className="w-6 h-6 text-cyan-400" />
          <h2 className="text-2xl font-bold text-white">Fault Diagnosis & Analysis</h2>
        </div>
        
        {/* Force Anomaly Test Button */}
        <div className="flex items-center space-x-3">
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value as 'HIGH' | 'MEDIUM' | 'LOW')}
            className="px-3 py-2 bg-[#0a1628] border border-cyan-900/30 rounded text-sm text-white focus:outline-none focus:border-cyan-500"
            disabled={isLoading}
          >
            <option value="HIGH">HIGH Severity</option>
            <option value="MEDIUM">MEDIUM Severity</option>
            <option value="LOW">LOW Severity</option>
          </select>
          
          <button
            onClick={handleForceAnomaly}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white font-semibold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                <span>Force Anomaly Test</span>
              </>
            )}
          </button>
        </div>
      </div>

      {anomalyDetection?.injected && (
        <div className="bg-orange-900/20 border border-orange-500/50 rounded-lg p-4">
          <div className="flex items-center space-x-2 text-orange-400">
            <Zap className="w-5 h-5" />
            <span className="font-semibold">TEST MODE: Anomaly Injected for Demo</span>
          </div>
          <p className="text-sm text-orange-300/70 mt-1">
            This is a simulated anomaly for testing the complete AI diagnosis pipeline (Detection → RCA → Explanation)
          </p>
        </div>
      )}

      {/* Anomaly Detection Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Real-time Anomaly Detection</h3>
          <AnomalyPanel />
        </div>

        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Detection Status</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-[#051020] rounded border border-cyan-900/20">
              <span className="text-gray-400">Status</span>
              <span className={`px-3 py-1 rounded text-sm font-semibold ${
                anomalyDetection?.detected 
                  ? 'bg-red-900/30 text-red-400' 
                  : 'bg-green-900/30 text-green-400'
              }`}>
                {anomalyDetection?.detected ? 'ANOMALY DETECTED' : 'NOMINAL'}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[#051020] rounded border border-cyan-900/20">
              <span className="text-gray-400">Confidence</span>
              <span className="text-cyan-400 font-mono">{((anomalyDetection?.probability ?? 0) * 100).toFixed(2)}%</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[#051020] rounded border border-cyan-900/20">
              <span className="text-gray-400">Severity</span>
              <span className={`text-sm font-semibold ${
                anomalyDetection?.severity === 'CRITICAL' ? 'text-red-400' :
                anomalyDetection?.severity === 'HIGH' ? 'text-orange-400' :
                anomalyDetection?.severity === 'MEDIUM' ? 'text-yellow-400' :
                'text-green-400'
              }`}>
                {anomalyDetection?.severity || 'LOW'}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[#051020] rounded border border-cyan-900/20">
              <span className="text-gray-400">Last Updated</span>
              <span className="text-gray-500 text-sm">{anomalyDetection?.timestamp ? new Date(anomalyDetection.timestamp).toLocaleTimeString() : 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Root Cause Analysis */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Root Cause Analysis (RCA)</h3>
        <KnowledgeGraphPanel />
        {rootCauses.length > 0 && (
          <div className="mt-4 text-xs text-gray-500">
            <p>
              Found {rootCauses.length} potential root causes. Knowledge Graph analyzed {kgStats?.nodes ?? 'N/A'}
              {' '}ADCS subsystem nodes and {kgStats?.relationships ?? 'N/A'} relationships.
            </p>
          </div>
        )}
      </div>

      {/* Detailed Diagnosis & Recommendations */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">XAI Analysis & Corrective Actions</h3>
        <DiagnosisPanel />
        {diagnosis && (
          <div className="mt-4 text-xs text-gray-500">
            {ragAvailable ? (
              <p>Explanation generated by LLM+RAG (Ollama) with ADCS knowledge retrieval.</p>
            ) : (
              <p>LLM unavailable. Deterministic diagnosis fallback is active with KG-based root-cause context.</p>
            )}
          </div>
        )}
      </div>

      {/* Interactive Diagnosis Chat */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Interactive Diagnosis Assistant</h3>
        <DiagnosisChatPanel />
        <div className="mt-4 text-xs text-gray-500">
          {ragAvailable ? (
            <p>Ask questions about anomaly patterns and corrective procedures. Chat answers use RAG over operations knowledge.</p>
          ) : (
            <p>Ask questions about anomaly patterns and corrective procedures. Chat answers use deterministic fallback until RAG is available.</p>
          )}
        </div>
      </div>
    </div>
  )
}
