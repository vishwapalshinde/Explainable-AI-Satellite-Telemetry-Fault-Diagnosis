'use client'

import { useState, useRef, useEffect } from 'react'
import { MessageCircle, Send, Loader2, Bot, User } from 'lucide-react'
import { useTelemetryStore } from '@/store/telemetryStore'
import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const CHAT_REQUEST_TIMEOUT_MS = 120000
const CHAT_MESSAGES_STORAGE_KEY = 'diagnosis_chat_messages_v1'
const CHAT_SESSION_STORAGE_KEY = 'diagnosis_chat_session_id_v1'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  actions?: string[]
  method?: string
  sourceReferences?: string[]
  timestamp: Date
}

const buildWelcomeMessage = (): ChatMessage => ({
  role: 'assistant',
  content: "Hello! I'm your AI diagnosis assistant. I can help explain anomalies, root causes, and provide guidance on corrective actions. Ask me anything about the current telemetry analysis!",
  timestamp: new Date()
})

export default function DiagnosisChatPanel() {
  const { anomalyDetection, rootCauses, diagnosis } = useTelemetryStore()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isHydrated, setIsHydrated] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sessionIdRef = useRef(`web_session_${Date.now()}`)

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Restore chat state from browser storage on mount
  useEffect(() => {
    try {
      const savedSessionId = localStorage.getItem(CHAT_SESSION_STORAGE_KEY)
      if (savedSessionId) {
        sessionIdRef.current = savedSessionId
      } else {
        localStorage.setItem(CHAT_SESSION_STORAGE_KEY, sessionIdRef.current)
      }

      const savedMessagesRaw = localStorage.getItem(CHAT_MESSAGES_STORAGE_KEY)
      if (savedMessagesRaw) {
        const parsed = JSON.parse(savedMessagesRaw) as Array<{
          role: 'user' | 'assistant'
          content: string
          actions?: string[]
          method?: string
          sourceReferences?: string[]
          timestamp: string
        }>

        const hydratedMessages: ChatMessage[] = parsed.map((msg) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }))
        setMessages(hydratedMessages)
      }
    } catch (error) {
      console.warn('Unable to restore diagnosis chat history:', error)
    } finally {
      setIsHydrated(true)
    }
  }, [])

  // Persist chat messages when they change
  useEffect(() => {
    if (!isHydrated) return

    try {
      localStorage.setItem(
        CHAT_MESSAGES_STORAGE_KEY,
        JSON.stringify(messages.map((msg) => ({
          ...msg,
          timestamp: msg.timestamp.toISOString()
        })))
      )
    } catch (error) {
      console.warn('Unable to persist diagnosis chat history:', error)
    }
  }, [messages, isHydrated])

  // Add welcome message only when no persisted messages exist
  useEffect(() => {
    if (isHydrated && messages.length === 0) {
      setMessages([buildWelcomeMessage()])
    }
  }, [isHydrated, messages.length])

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    // Add user message immediately
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const recentHistory = [...messages, userMessage].slice(-6).map((m) => ({
        role: m.role,
        content: m.content
      }))

      // Build context for API
      const context = {
        detection: {
          is_anomaly: anomalyDetection?.detected,
          probability: anomalyDetection?.probability,
          severity: anomalyDetection?.severity,
          characteristics: anomalyDetection?.characteristics || []
        },
        diagnosis_mode: diagnosis?.explanation_mode,
        source_references: diagnosis?.source_references || [],
        root_causes: rootCauses.map(rc => ({
          fault_name: rc.fault || rc.fault_name,
          confidence: rc.confidence,
          description: rc.description,
          severity: rc.severity
        })),
        channel: 'CADC0872', // Default magnetometer channel
        features: diagnosis?.evidence_summary || {},
        chat_history: recentHistory
      }

      // Send to backend chat API
      const response = await axios.post(
        `${API_BASE_URL}/api/v1/diagnosis/chat`,
        {
          message: input,
          context: context,
          session_id: sessionIdRef.current
        },
        {
          timeout: CHAT_REQUEST_TIMEOUT_MS
        }
      )

      // Add AI response
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.data.response,
        actions: response.data.actions || [],
        method: response.data.method || response.data.explanation_mode,
        sourceReferences: response.data.source_references || [],
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])

    } catch (error: any) {
      console.error('Chat error:', error)
      
      // Fallback error message
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: error.response?.data?.detail || 
                 error.message || 
                 'Unable to connect to diagnosis chat service. Real-time diagnosis remains available in the detection and root-cause panels.',
        timestamp: new Date()
      }

      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleActionClick = (action: string) => {
    setInput(action)
  }

  const handleClearChat = () => {
    const confirmed = window.confirm('Clear this chat history and start a new session?')
    if (!confirmed) return

    const newSessionId = `web_session_${Date.now()}`
    sessionIdRef.current = newSessionId

    setMessages([buildWelcomeMessage()])
    setInput('')

    localStorage.removeItem(CHAT_MESSAGES_STORAGE_KEY)
    localStorage.setItem(CHAT_SESSION_STORAGE_KEY, newSessionId)
  }

  return (
    <div className="flex flex-col h-[600px] bg-[#0a1628]/50 border border-cyan-900/30 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-cyan-900/30 bg-[#051020]">
        <div className="flex items-center space-x-2">
          <MessageCircle className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">
            Interactive Diagnosis Chat
          </h3>
        </div>
        <div className="flex items-center space-x-2 text-xs text-gray-500">
          <button
            onClick={handleClearChat}
            className="px-2 py-1 text-[11px] rounded border border-cyan-900/40 hover:border-cyan-700/60 hover:text-cyan-300 transition-all"
            disabled={isLoading}
          >
            Clear Chat
          </button>
          <Bot className="w-4 h-4" />
          <span>AI Assistant {anomalyDetection?.detected ? '(Active)' : '(Standby)'}</span>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`flex items-start space-x-3 max-w-[80%] ${
                msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              {/* Avatar */}
              <div
                className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                  msg.role === 'user'
                    ? 'bg-cyan-600'
                    : 'bg-gradient-to-br from-purple-600 to-blue-600'
                }`}
              >
                {msg.role === 'user' ? (
                  <User className="w-4 h-4 text-white" />
                ) : (
                  <Bot className="w-4 h-4 text-white" />
                )}
              </div>

              {/* Message Content */}
              <div className="flex flex-col">
                <div
                  className={`rounded-lg p-3 ${
                    msg.role === 'user'
                      ? 'bg-cyan-900/40 border border-cyan-700/50'
                      : 'bg-[#051020] border border-cyan-900/30'
                  }`}
                >
                  <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </p>

                  {(msg.method || msg.sourceReferences?.length) && (
                    <div className="mt-2 text-[11px] text-cyan-400/70 space-y-1">
                      {msg.method && <div>Mode: {msg.method}</div>}
                      {msg.sourceReferences && msg.sourceReferences.length > 0 && (
                        <div>Sources: {msg.sourceReferences.join(', ')}</div>
                      )}
                    </div>
                  )}

                  {/* Action Buttons */}
                  {msg.actions && msg.actions.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <p className="text-xs text-cyan-400 font-semibold">Suggested Actions:</p>
                      <div className="space-y-1">
                        {msg.actions.map((action, actionIdx) => (
                          <button
                            key={actionIdx}
                            onClick={() => handleActionClick(`How do I: ${action}`)}
                            className="w-full text-left text-xs text-gray-300 hover:text-cyan-400 p-2 rounded bg-cyan-900/20 hover:bg-cyan-900/40 border border-cyan-900/30 hover:border-cyan-700/50 transition-all"
                          >
                            {actionIdx + 1}. {action}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Timestamp */}
                <span className="text-xs text-gray-600 mt-1">
                  {msg.timestamp.toLocaleTimeString()}
                </span>
              </div>
            </div>
          </div>
        ))}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="bg-[#051020] border border-cyan-900/30 rounded-lg p-3">
                <div className="flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                  <span className="text-sm text-gray-400">AI is thinking... this can take up to 2 minutes</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-cyan-900/30 p-4 bg-[#051020]">
        <div className="flex items-end space-x-3">
          <div className="flex-1">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about the anomaly, root causes, or corrective actions..."
              className="w-full px-4 py-3 bg-[#0a1628] border border-cyan-900/30 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 resize-none"
              rows={2}
              disabled={isLoading}
            />
            <div className="mt-2 text-xs text-gray-600">
              Press Enter to send, Shift+Enter for new line
            </div>
          </div>

          <button
            onClick={handleSendMessage}
            disabled={!input.trim() || isLoading}
            className="flex items-center justify-center w-12 h-12 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Quick Actions */}
        {anomalyDetection?.detected && (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={() => setInput("What caused this anomaly?")}
              className="text-xs px-3 py-1 bg-cyan-900/20 hover:bg-cyan-900/40 text-cyan-400 rounded border border-cyan-900/30 hover:border-cyan-700/50 transition-all"
              disabled={isLoading}
            >
              What caused this?
            </button>
            <button
              onClick={() => setInput("What should I do first?")}
              className="text-xs px-3 py-1 bg-cyan-900/20 hover:bg-cyan-900/40 text-cyan-400 rounded border border-cyan-900/30 hover:border-cyan-700/50 transition-all"
              disabled={isLoading}
            >
              What should I do?
            </button>
            <button
              onClick={() => setInput("Is this critical?")}
              className="text-xs px-3 py-1 bg-cyan-900/20 hover:bg-cyan-900/40 text-cyan-400 rounded border border-cyan-900/30 hover:border-cyan-700/50 transition-all"
              disabled={isLoading}
            >
              Is this critical?
            </button>
            <button
              onClick={() => setInput("Explain the root causes in detail")}
              className="text-xs px-3 py-1 bg-cyan-900/20 hover:bg-cyan-900/40 text-cyan-400 rounded border border-cyan-900/30 hover:border-cyan-700/50 transition-all"
              disabled={isLoading}
            >
              Explain root causes
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
