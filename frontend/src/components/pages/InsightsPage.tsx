'use client'

import { Brain } from 'lucide-react'
import DiagnosisPanel from '@/components/DiagnosisPanel'
import KnowledgeGraphPanel from '@/components/KnowledgeGraphPanel'
import { useEffect } from 'react'
import { useTelemetryStore } from '@/store/telemetryStore'

export default function InsightsPage() {
  const { diagnosis, rootCauses, kgStats, anomalyDetection, runtimeStats, fetchKnowledgeGraphStats } = useTelemetryStore()

  useEffect(() => {
    fetchKnowledgeGraphStats()
  }, [fetchKnowledgeGraphStats])

  const modelInfo = runtimeStats?.model_info
  const modelLabel = modelInfo?.architecture || 'FCNN'
  const explainabilityLabel = diagnosis?.explanation_mode === 'ollama_rag' ? 'LLM+RAG (Live)' : diagnosis?.explanation_mode === 'nominal' ? 'Nominal Rules' : 'Deterministic Fallback'
  const liveScore = anomalyDetection ? `${((1 - anomalyDetection.probability) * 100).toFixed(2)}%` : 'N/A'
  const inputFeatures = modelInfo?.input_features ?? 18
  const hiddenLayers = modelInfo?.hidden_layers?.join('→') || '128→64→32'

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3 mb-6">
        <Brain className="w-6 h-6 text-cyan-400" />
        <h2 className="text-2xl font-bold text-white">Explainable AI (XAI) Insights</h2>
      </div>

      {/* Model Information */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-4">
          <p className="text-xs text-cyan-400 uppercase tracking-wider">Model</p>
          <p className="text-lg font-bold text-white mt-1">{modelLabel}</p>
          <p className="text-xs text-gray-500 mt-2">Fully Connected Neural Network with Batch Normalization & Dropout</p>
        </div>
        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-4">
          <p className="text-xs text-cyan-400 uppercase tracking-wider">Current Health Score</p>
          <p className="text-lg font-bold text-green-400 mt-1">{liveScore}</p>
          <p className="text-xs text-gray-500 mt-2">Derived from live anomaly probability</p>
        </div>
        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-4">
          <p className="text-xs text-cyan-400 uppercase tracking-wider">Explainability</p>
          <p className="text-lg font-bold text-cyan-400 mt-1">{explainabilityLabel}</p>
          <p className="text-xs text-gray-500 mt-2">Mode from latest diagnosis response</p>
        </div>
      </div>

      {/* Knowledge Graph Insights */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Knowledge Graph Reasoning</h3>
        <KnowledgeGraphPanel />
        {kgStats && (
          <div className="mt-4 grid grid-cols-3 gap-4 pt-4 border-t border-cyan-900/20">
            <div>
              <p className="text-xs text-gray-400">Total Nodes</p>
              <p className="text-xl font-bold text-cyan-400">{kgStats.nodes}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Relationships</p>
              <p className="text-xl font-bold text-cyan-400">{kgStats.relationships}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Subsystems</p>
              <p className="text-xl font-bold text-cyan-400">9</p>
            </div>
          </div>
        )}
      </div>

      {/* AI-Generated Explanation */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">AI-Generated Diagnosis & Recommendations</h3>
        <DiagnosisPanel />
      </div>

      {/* Methodology */}
      <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">XAI Pipeline Architecture</h3>
        <div className="space-y-3 text-sm">
          <div className="flex items-start space-x-3 p-3 bg-[#051020] rounded border border-cyan-900/20">
            <div className="w-6 h-6 rounded-full bg-cyan-500/20 flex items-center justify-center flex-shrink-0 text-cyan-400 text-xs font-bold">1</div>
            <div>
              <p className="font-semibold text-cyan-400">Data Ingestion</p>
              <p className="text-gray-400 text-xs mt-1">Load ESA OPS-SAT ADCS telemetry (9 channels, 2125 segments)</p>
            </div>
          </div>
          <div className="flex items-start space-x-3 p-3 bg-[#051020] rounded border border-cyan-900/20">
            <div className="w-6 h-6 rounded-full bg-cyan-500/20 flex items-center justify-center flex-shrink-0 text-cyan-400 text-xs font-bold">2</div>
            <div>
              <p className="font-semibold text-cyan-400">Data Processing</p>
              <p className="text-gray-400 text-xs mt-1">Normalize, scale, and extract features for ML</p>
            </div>
          </div>
          <div className="flex items-start space-x-3 p-3 bg-[#051020] rounded border border-cyan-900/20">
            <div className="w-6 h-6 rounded-full bg-cyan-500/20 flex items-center justify-center flex-shrink-0 text-cyan-400 text-xs font-bold">3</div>
            <div>
              <p className="font-semibold text-cyan-400">FCNN Inference</p>
              <p className="text-gray-400 text-xs mt-1">{`${inputFeatures}→${hiddenLayers}→1`} with batch normalization & dropout</p>
            </div>
          </div>
          <div className="flex items-start space-x-3 p-3 bg-[#051020] rounded border border-cyan-900/20">
            <div className="w-6 h-6 rounded-full bg-cyan-500/20 flex items-center justify-center flex-shrink-0 text-cyan-400 text-xs font-bold">4</div>
            <div>
              <p className="font-semibold text-cyan-400">Root Cause Analysis</p>
              <p className="text-gray-400 text-xs mt-1">Query 24-node knowledge graph for fault analysis</p>
            </div>
          </div>
          <div className="flex items-start space-x-3 p-3 bg-[#051020] rounded border border-cyan-900/20">
            <div className="w-6 h-6 rounded-full bg-cyan-500/20 flex items-center justify-center flex-shrink-0 text-cyan-400 text-xs font-bold">5</div>
            <div>
              <p className="font-semibold text-cyan-400">LLM+RAG Explanation</p>
              <p className="text-gray-400 text-xs mt-1">Generate human-readable explanation grounded in knowledge base</p>
            </div>
          </div>
        </div>
      </div>

      {/* Current Analysis Status */}
      {anomalyDetection && (
        <div className="bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Current Analysis</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Status</span>
              <span className={`font-semibold ${anomalyDetection.detected ? 'text-red-400' : 'text-green-400'}`}>
                {anomalyDetection.detected ? 'Anomaly Detected' : 'Normal Operation'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Confidence Score</span>
              <span className="text-cyan-400 font-mono">{(anomalyDetection.probability * 100).toFixed(2)}%</span>
            </div>
            {rootCauses.length > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-400">Top Root Cause</span>
                <span className="text-orange-400">{rootCauses[0].fault}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
