import { create } from 'zustand'
import axios from 'axios'
import { 
  TelemetryFeatures 
} from '@/lib/telemetryGenerator'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface TelemetryData {
  channel: string
  value: number
  timestamp: string
  anomaly: boolean
  features?: TelemetryFeatures
}

interface AnomalyDetection {
  probability: number
  detected: boolean
  severity: string
  characteristics?: string[]
  timestamp?: string
  injected?: boolean
}

interface RootCause {
  fault: string
  fault_name?: string
  confidence: number
  description?: string
  severity?: string
}

interface Diagnosis {
  explanation: string
  severity: string
  corrective_actions: string[]
  confidence: number
  explanation_mode?: string
  source_references?: string[]
  evidence_summary?: {
    anomaly_probability?: number
    affected_channels?: string[]
    characteristics?: string[]
    probable_root_causes?: Array<{
      fault_id: string
      fault_name: string
      confidence: number
    }>
  }
}

interface KnowledgeGraphStats {
  nodes: number
  relationships: number
}

interface RuntimeStats {
  model_info?: {
    architecture?: string
    input_features?: number
    hidden_layers?: number[]
    parameters?: number
  }
  knowledge_graph?: KnowledgeGraphStats
  system?: {
    environment?: string
    device?: string
  }
}

type PageView = 'dashboard' | 'satellites' | 'telemetry' | 'diagnosis' | 'insights' | 'datastore' | 'settings'

interface TelemetryState {
  // Navigation
  currentPage: PageView
  setCurrentPage: (page: PageView) => void
  
  // Telemetry data
  telemetryData: TelemetryData[]
  currentChannels: string[]
  currentFeatures: Record<string, TelemetryFeatures>
  
  // Anomaly Detection
  anomalyDetection: AnomalyDetection | null
  rootCauses: RootCause[]
  
  // Diagnosis
  diagnosis: Diagnosis | null
  
  // System Status
  systemStatus: any
  isConnected: boolean
  isLoading: boolean
  error: string | null
  
  // Knowledge Graph
  kgStats: KnowledgeGraphStats | null
  runtimeStats: RuntimeStats | null
  
  // Real-time Processing
  isProcessing: boolean
  lastProcessingTime: string | null
  
  // Actions
  fetchSystemStatus: () => Promise<void>
  fetchKnowledgeGraphStats: () => Promise<void>
  detectAnomaly: (features: any, channel: string) => Promise<void>
  diagnoseFault: (features: any, channels: string[]) => Promise<void>
  addTelemetryData: (data: TelemetryData) => void
  generateAndProcessTelemetry: () => Promise<void>
  performFullDiagnosis: () => Promise<void>
  simulateTelemetry: () => void
  forceAnomaly: (severity?: 'HIGH' | 'MEDIUM' | 'LOW') => Promise<void>
}

export const useTelemetryStore = create<TelemetryState>((set, get) => ({
  // Navigation state
  currentPage: 'dashboard',
  setCurrentPage: (page: PageView) => set({ currentPage: page }),
  
  // Initial State
  isConnected: false,
  isLoading: false,
  error: null,
  telemetryData: [],
  currentChannels: ['CADC0872', 'CADC0873', 'CADC0874', 'CADC0875', 'CADC0876', 'CADC0877', 'CADC0878', 'CADC0879', 'CADC0880'],
  currentFeatures: {},
  anomalyDetection: null,
  rootCauses: [],
  diagnosis: null,
  systemStatus: null,
  kgStats: null,
  runtimeStats: null,
  isProcessing: false,
  lastProcessingTime: null,
  
  // Fetch System Status
  fetchSystemStatus: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.get(`${API_BASE_URL}/health`, { timeout: 5000 })
      set({ 
        isConnected: true,
        systemStatus: response.data,
        isLoading: false
      })
    } catch (error) {
      console.error('Failed to fetch system status:', error)
      set({ 
        isConnected: false, 
        isLoading: false,
        error: 'Failed to connect to backend API'
      })
    }
  },
  
  // Fetch Knowledge Graph Stats
  fetchKnowledgeGraphStats: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/stats`, { timeout: 5000 })
      set({ 
        kgStats: response.data.knowledge_graph,
        runtimeStats: response.data
      })
    } catch (error) {
      console.error('Failed to fetch KG stats:', error)
    }
  },
  
  // Detect Anomaly
  detectAnomaly: async (features: any, channel: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/detect`, {
        features,
        channel,
        timestamp: new Date().toISOString()
      }, { timeout: 10000 })

      const detection = {
        ...response.data,
        detected: response.data?.detected ?? response.data?.anomaly_detected ?? false
      }

      set({ anomalyDetection: detection, isLoading: false })
    } catch (error) {
      console.error('Anomaly detection failed:', error)
      set({ 
        error: 'Anomaly detection failed',
        isLoading: false
      })
    }
  },
  
  // Diagnose Fault
  diagnoseFault: async (features: any, channels: string[]) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/diagnose`, {
        features,
        channels,
        timestamp: new Date().toISOString()
      }, { timeout: 15000 })

      const anomalyDetection = {
        ...response.data.anomaly_detection,
        detected: response.data?.anomaly_detection?.detected ?? response.data?.anomaly_detection?.anomaly_detected ?? false
      }
      
      set({
        anomalyDetection,
        rootCauses: response.data.root_causes,
        diagnosis: response.data.diagnosis,
        isLoading: false
      })
    } catch (error) {
      console.error('Fault diagnosis failed:', error)
      set({ 
        error: 'Fault diagnosis failed',
        isLoading: false
      })
    }
  },
  
  // Add Telemetry Data
  addTelemetryData: (data: TelemetryData) => {
    set((state) => ({
      telemetryData: [...state.telemetryData.slice(-999), data]
    }))
  },
  
  // Generate and Process Real Telemetry with Backend AI
  generateAndProcessTelemetry: async () => {
    const state = get()
    if (state.isProcessing) return

    set({ isProcessing: true, error: null })

    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/telemetry/next?include_all_channels=true`, { timeout: 15000 })
      const payload = response.data

      const channelSnapshots: Array<any> = payload.channels || []
      const featuresByChannel: Record<string, TelemetryFeatures> = {}
      const channelDetections: Record<string, any> = payload.channel_detections || {}

      channelSnapshots.forEach((item: any) => {
        const channel = item.channel
        const itemFeatures = item.features || {}
        const channelDetection = channelDetections[channel] || {}
        featuresByChannel[channel] = itemFeatures as TelemetryFeatures

        get().addTelemetryData({
          channel,
          value: Number(item.value ?? itemFeatures.mean ?? 0),
          timestamp: payload.timestamp || new Date().toISOString(),
          anomaly: Boolean(channelDetection?.detected),
          features: itemFeatures as TelemetryFeatures
        })
      })

      set({ 
        currentChannels: channelSnapshots.map((item: any) => item.channel),
        currentFeatures: featuresByChannel,
        anomalyDetection: {
          ...payload.anomaly_detection,
          detected: payload?.anomaly_detection?.detected ?? payload?.anomaly_detection?.anomaly_detected ?? false
        },
        rootCauses: payload.root_causes || [],
        diagnosis: payload.diagnosis || null,
        lastProcessingTime: payload.timestamp || new Date().toISOString()
      })

    } catch (error) {
      console.error('Telemetry generation failed:', error)
      set({ error: 'Failed to stream telemetry snapshot from backend dataset' })
    } finally {
      set({ isProcessing: false })
    }
  },
  
  // Perform Full AI Diagnosis (Detection + Root Cause + Explanation)
  performFullDiagnosis: async () => {
    const state = get()
    const { currentFeatures, currentChannels } = state
    
    if (Object.keys(currentFeatures).length === 0) {
      console.warn('No telemetry features available for diagnosis')
      return
    }
    
    set({ isLoading: true, error: null })
    
    try {
      // Aggregate features from magnetometer channels (ADCS subsystem focus)
      const magnetometerChannels = ['CADC0872', 'CADC0873', 'CADC0874']
      const aggregatedFeatures = currentFeatures['CADC0872'] // Primary channel
      
      const response = await axios.post(`${API_BASE_URL}/api/v1/diagnose`, {
        features: aggregatedFeatures,
        channels: magnetometerChannels,
        timestamp: new Date().toISOString()
      }, { timeout: 20000 })

      const anomalyDetection = {
        ...response.data.anomaly_detection,
        detected: response.data?.anomaly_detection?.detected ?? response.data?.anomaly_detection?.anomaly_detected ?? false
      }
      
      set({
        anomalyDetection,
        rootCauses: response.data.root_causes || [],
        diagnosis: response.data.diagnosis,
        isLoading: false,
        lastProcessingTime: new Date().toISOString()
      })
      
      console.log('✅ Full AI diagnosis completed:', response.data)
      
    } catch (error: any) {
      console.error('Full diagnosis failed:', error)
      set({ 
        error: `Diagnosis failed: ${error.message}`,
        isLoading: false
      })
    }
  },
  
  // Simulate Telemetry (fallback for display only)
  simulateTelemetry: () => {
    const channels = get().currentChannels

    channels.forEach((channel, idx) => {
      const baseValue = -2.1e-5 + (idx * 1e-6)
      const variation = (Math.random() - 0.5) * 0.1
      const value = baseValue + (baseValue * variation)
      
      get().addTelemetryData({
        channel,
        value,
        timestamp: new Date().toISOString(),
        anomaly: false
      })
    })
  },
  
  // Force Anomaly Injection (for testing/demo)
  forceAnomaly: async (severity: 'HIGH' | 'MEDIUM' | 'LOW' = 'HIGH') => {
    set({ isLoading: true, error: null })
    
    try {
      const magnetometerChannels = ['CADC0872', 'CADC0873', 'CADC0874']
      
      const response = await axios.post(`${API_BASE_URL}/api/v1/inject-anomaly`, {
        severity,
        channels: magnetometerChannels,
        full_diagnosis: true
      }, { timeout: 20000 })
      
      const anomalyDetection = {
        ...response.data.anomaly_detection,
        detected: response.data?.anomaly_detection?.detected ?? response.data?.anomaly_detection?.anomaly_detected ?? true
      }
      
      set({
        anomalyDetection,
        rootCauses: response.data.root_causes || [],
        diagnosis: response.data.diagnosis,
        isLoading: false,
        lastProcessingTime: new Date().toISOString()
      })
      
      console.log('🧪 Forced anomaly injected:', response.data)
      
    } catch (error: any) {
      console.error('Force anomaly failed:', error)
      set({ 
        error: `Force anomaly failed: ${error.message}`,
        isLoading: false
      })
    }
  }
}))
