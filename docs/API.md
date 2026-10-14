# API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication
Currently no authentication required for development. Production deployment will use JWT tokens.

---

## Endpoints

### 1. Health Check

**GET** `/health`

Check API health and component status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "components": {
    "fcnn_model": true,
    "data_processor": true,
    "knowledge_graph": true,
    "rag_explainer": true,
    "telemetry_replay": true,
    "xai_fallback_available": true
  }
}
```

---

### 2. System Statistics

**GET** `/api/v1/stats`

Get system statistics and model information.

**Response:**
```json
{
  "model_info": {
    "architecture": "FCNN",
    "input_features": 20,
    "hidden_layers": [128, 64, 32],
    "parameters": 15234
  },
  "knowledge_graph": {
    "nodes": 24,
    "relationships": 42
  },
  "system": {
    "environment": "development",
    "device": "cuda"
  }
}
```

---

### 3. Anomaly Detection

**POST** `/api/v1/detect`

Detect anomaly in telemetry data for a single channel.

**Request Body:**
```json
{
  "features": {
    "mean": 8.533e-07,
    "var": 3.494e-10,
    "std": 1.869e-05,
    "kurtosis": 0.631,
    "skew": 0.552,
    "n_peaks": 4,
    "smooth10_n_peaks": 3,
    "smooth20_n_peaks": 2,
    "diff_peaks": 4,
    "diff2_peaks": 6,
    "diff_var": 1.271e-10,
    "diff2_var": 2.961e-10,
    "gaps_squared": 279,
    "len_weighted": 280,
    "var_div_duration": 1.252e-12,
    "var_div_len": 1.248e-12,
    "duration": 279,
    "len": 280
  },
  "channel": "CADC0872",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Response:**
```json
{
  "anomaly_detected": true,
  "probability": 0.95,
  "channel": "CADC0872",
  "timestamp": "2024-01-01T00:00:00Z",
  "severity": "HIGH"
}
```

---

### 4. Complete Fault Diagnosis

**POST** `/api/v1/diagnose`

Run complete diagnosis pipeline including anomaly detection, root cause analysis, and explanation.

**Request Body:**
```json
{
  "features": {
    "mean": 8.533e-07,
    "var": 3.494e-10,
    "std": 1.869e-05,
    ...
  },
  "channels": ["CADC0872", "CADC0873"],
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Response:**
```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "anomaly_detection": {
    "probability": 0.95,
    "detected": true,
    "timestamp": "2024-01-01T00:00:00Z"
  },
  "affected_channels": ["CADC0872", "CADC0873"],
  "root_causes": [
    {
      "fault": "sensor_bias",
      "confidence": 0.85
    },
    {
      "fault": "thermal_anomaly",
      "confidence": 0.72
    },
    {
      "fault": "sensor_drift",
      "confidence": 0.58
    }
  ],
  "diagnosis": {
    "explanation": "The magnetometer X and Y axes are exhibiting correlated bias patterns consistent with a thermal-induced offset. This is likely caused by temperature variations affecting the sensor electronics...",
    "severity": "HIGH",
    "corrective_actions": [
      "Recalibrate affected magnetometer axes using Earth's magnetic field model",
      "Update bias compensation parameters in the flight software",
      "Review thermal telemetry for correlation with sensor readings",
      "Schedule enhanced monitoring for next orbital cycle"
    ],
    "confidence": 0.85
  }
}
```

---

### 5. Knowledge Graph Nodes

**GET** `/api/v1/knowledge-graph/nodes`

Get all nodes in the ADCS knowledge graph.

**Response:**
```json
{
  "nodes": [
    {
      "id": "adcs_subsystem",
      "type": "subsystem",
      "name": "ADCS",
      "description": "Attitude Determination and Control System"
    },
    {
      "id": "CADC0872",
      "type": "channel",
      "name": "Magnetometer X-axis",
      "description": "Magnetic field X component"
    },
    ...
  ]
}
```

---

### 6. Next Telemetry Replay Snapshot

**GET** `/api/v1/telemetry/next?include_all_channels=true`

Returns the next replay snapshot from `segments.csv`, including per-channel detections.

**Key Response Fields:**
- `channels`: channel snapshots with value/features
- `channel_detections`: anomaly output for each channel
- `affected_channels`: channels selected as anomalous for RCA
- `root_causes`: KG-ranked probable faults
- `diagnosis`: explanation payload (LLM optional)

**Note:**
`include_llm_explanation` is `false` by default to keep replay low-latency.

---

### 7. Interactive Diagnosis Chat

**POST** `/api/v1/diagnosis/chat`

Ask contextual follow-up questions using latest detection and root-cause evidence.

**Request Body:**
```json
{
  "message": "What should operator do first?",
  "context": {
    "detection": {
      "probability": 0.91,
      "severity": "HIGH",
      "characteristics": ["mean_shift", "high_variance"]
    },
    "root_causes": [
      {"fault": "magnetometer_calibration_drift", "confidence": 0.94}
    ],
    "channel": "CADC0872",
    "chat_history": []
  },
  "session_id": "web_session_123"
}
```

**Behavior:**
- Uses Ollama-RAG path when available
- Falls back to deterministic response if LLM unavailable or timeout exceeded
- Timeout controlled by `CHAT_RESPONSE_TIMEOUT_SECONDS` (default: 60)

**Response Fields:**
- `response`
- `actions`
- `confidence`
- `method` / `explanation_mode`
- `source_references`
- `evidence_summary`

---

## Error Responses

All endpoints may return error responses:

**400 Bad Request:**
```json
{
  "detail": "Invalid request format"
}
```

**503 Service Unavailable:**
```json
{
  "detail": "Model not loaded"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error message"
}
```

---

## Rate Limiting

No rate limiting in development. Production will enforce:
- 100 requests/minute per IP
- 1000 requests/hour per IP

---

## WebSocket Support (Future)

Real-time telemetry streaming will be available via WebSocket:
```
ws://localhost:8000/ws/telemetry
```

---

## Interactive API Documentation

Visit http://localhost:8000/docs for interactive Swagger UI.
