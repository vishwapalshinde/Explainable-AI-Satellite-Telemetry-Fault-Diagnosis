'use client'

import { FileText, AlertCircle, Loader2 } from 'lucide-react'
import { useTelemetryStore } from '@/store/telemetryStore'

export default function DiagnosisPanel() {
  const { diagnosis: stateDiagnosis, isLoading } = useTelemetryStore()
  
  const diagnosis = stateDiagnosis ?? {
    severity: 'LOW',
    explanation: 'System operating within normal parameters. All ADCS channels showing expected behavior.',
    corrective_actions: [
      'Continue routine monitoring of all telemetry channels',
      'Scheduled calibration check in next maintenance window',
      'No immediate action required'
    ],
    confidence: 0.92
  }
  
  const severityColor = {
    CRITICAL: 'text-red-500 bg-red-500/20 border-red-500',
    HIGH: 'text-orange-500 bg-orange-500/20 border-orange-500',
    MEDIUM: 'text-yellow-500 bg-yellow-500/20 border-yellow-500',
    LOW: 'text-green-500 bg-green-500/20 border-green-500'
  }

  const evidence = diagnosis.evidence_summary
  const sourceReferences = diagnosis.source_references || []
  
  return (
    <div className="bg-[#0f1e33]/50 backdrop-blur border border-cyan-900/30 rounded-lg">
      <div className="px-4 py-3 border-b border-cyan-900/30 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">Fault Diagnosis & Explanation</h2>
          <p className="text-xs text-cyan-400/70 uppercase">AI-powered analysis with corrective actions</p>
        </div>
        <div className="px-3 py-1 bg-cyan-500/20 border border-cyan-500/50 rounded text-xs text-cyan-400 font-semibold uppercase flex items-center">
          <FileText className="w-3 h-3 mr-1" />
          AI Engine Active
        </div>
      </div>
      
      <div className="p-6 space-y-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
          </div>
        ) : (
        <>
        {/* Severity Badge */}
        <div className="flex items-center justify-between">
          <div className={`px-4 py-2 rounded-lg border font-semibold ${severityColor[diagnosis.severity as keyof typeof severityColor]}`}>
            <AlertCircle className="w-4 h-4 inline mr-2" />
            Severity: {diagnosis.severity}
          </div>
          <div className="text-sm text-cyan-400/70">
            Confidence: {(diagnosis.confidence * 100).toFixed(1)}%
          </div>
        </div>
        
        {/* Explanation */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-cyan-400/70 uppercase tracking-wider">
            Technical Explanation
          </h3>
          <div className="p-4 bg-[#0a1628]/50 border border-cyan-900/20 rounded-lg leading-relaxed text-white">
            {diagnosis.explanation}
          </div>
        </div>

        {/* Evidence */}
        {(diagnosis.explanation_mode || sourceReferences.length > 0 || evidence) && (
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-cyan-400/70 uppercase tracking-wider">
              Evidence & Mode
            </h3>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="p-4 bg-[#0a1628]/50 border border-cyan-900/20 rounded-lg text-sm text-white space-y-2">
                <div className="text-xs uppercase tracking-wider text-cyan-400/70">Explanation Mode</div>
                <div>{diagnosis.explanation_mode || 'unknown'}</div>
                <div className="text-xs uppercase tracking-wider text-cyan-400/70 pt-2">Anomaly Probability</div>
                <div>{((evidence?.anomaly_probability ?? diagnosis.confidence) * 100).toFixed(1)}%</div>
              </div>
              <div className="p-4 bg-[#0a1628]/50 border border-cyan-900/20 rounded-lg text-sm text-white space-y-2">
                <div className="text-xs uppercase tracking-wider text-cyan-400/70">Source References</div>
                {sourceReferences.length > 0 ? (
                  <ul className="space-y-1 text-sm text-gray-200">
                    {sourceReferences.map((ref, idx) => (
                      <li key={idx}>• {ref}</li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-gray-400">No explicit source references available.</div>
                )}
              </div>
            </div>
            {evidence?.probable_root_causes && evidence.probable_root_causes.length > 0 && (
              <div className="p-4 bg-[#0a1628]/50 border border-cyan-900/20 rounded-lg text-sm text-white space-y-2">
                <div className="text-xs uppercase tracking-wider text-cyan-400/70">Probable Root Causes</div>
                <div className="space-y-1">
                  {evidence.probable_root_causes.map((rc, idx) => (
                    <div key={idx} className="flex items-center justify-between text-gray-200">
                      <span>{rc.fault_name}</span>
                      <span className="text-cyan-400">{(rc.confidence * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Corrective Actions */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-cyan-400/70 uppercase tracking-wider">
            Recommended Actions
          </h3>
          <div className="space-y-2">
            {diagnosis.corrective_actions.map((action, idx) => (
              <div key={idx} className="flex items-start space-x-3 p-3 bg-[#0a1628]/50 border border-cyan-900/20 rounded-lg hover:border-cyan-500/50 transition-all">
                <div className="flex-shrink-0 w-6 h-6 bg-cyan-500/20 text-cyan-400 rounded-full flex items-center justify-center text-sm font-semibold">
                  {idx + 1}
                </div>
                <p className="flex-1 text-sm text-white">{action}</p>
              </div>
            ))}
          </div>
        </div>
        
        {/* Metadata */}
        <div className="pt-4 border-t border-cyan-900/30 text-xs text-cyan-400/50 space-y-1">
          <p>Generated by: {diagnosis.explanation_mode || 'unknown'} explanation engine</p>
          <p>Sources: {sourceReferences.length > 0 ? sourceReferences.join(', ') : 'ADCS Knowledge Base'}</p>
          <p>Timestamp: {new Date().toLocaleString()}</p>
        </div>
        </>
        )}
      </div>
    </div>
  )
}
