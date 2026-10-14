# System Architecture

## Overview
Production-grade explainable AI system for satellite telemetry fault diagnosis.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                    │
├──────────────────────────────────────────────────────────────────┤
│  ESA OPS-SAT Dataset → Telemetry Ingestor → Data Processor       │
│  (9 ADCS Channels)     (Validation)         (Normalization)      │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                  ANOMALY DETECTION LAYER                          │
├──────────────────────────────────────────────────────────────────┤
│  FCNN Model (Primary)          AdaBoost (Baseline)               │
│  - Dropout & Batch Norm        - Ensemble decision trees         │
│  - >90% Accuracy               - Fast inference                  │
│  - Binary Classification       - Feature importance              │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                ROOT CAUSE ANALYSIS LAYER                          │
├──────────────────────────────────────────────────────────────────┤
│  Knowledge Graph (NetworkX/Neo4j)                                │
│  - ADCS subsystem ontology                                       │
│  - Channel-to-fault mappings                                     │
│  - Probabilistic reasoning                                       │
│  - Confidence scoring                                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                EXPLAINABILITY LAYER (LLM + RAG)                   │
├──────────────────────────────────────────────────────────────────┤
│  RAG Pipeline:                                                    │
│  1. Knowledge Base (ADCS operations docs)                        │
│  2. Vector Store (ChromaDB)                                      │
│  3. Embeddings (sentence-transformers)                           │
│  4. LLM (Ollama/Llama3)                                          │
│  5. Explanation Generator                                        │
│  Output: Human-readable diagnosis + corrective actions           │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                     API LAYER (FastAPI)                           │
├──────────────────────────────────────────────────────────────────┤
│  REST Endpoints:                                                 │
│  - POST /api/v1/detect         (anomaly detection)               │
│  - POST /api/v1/diagnose       (complete diagnosis)              │
│  - GET  /api/v1/knowledge-graph (KG visualization)               │
│  - GET  /api/v1/stats          (system metrics)                  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│              FRONTEND LAYER (Next.js + TypeScript)                │
├──────────────────────────────────────────────────────────────────┤
│  Enterprise Dashboard Components:                                │
│  - 3D Satellite Viewer (Three.js)                                │
│  - Live Telemetry Panel (Real-time channel monitoring)           │
│  - Anomaly Detection Panel (Visual alerts)                       │
│  - Knowledge Graph Panel (Root cause visualization)              │
│  - Diagnosis Panel (Explanations + corrective actions)           │
└──────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend
- **Language**: Python 3.10+
- **Framework**: FastAPI (async, high-performance)
- **ML**: PyTorch 2.0+ (FCNN), Scikit-learn (AdaBoost)
- **Knowledge Graph**: NetworkX (in-memory), Neo4j (optional)
- **LLM**: Ollama (local), LangChain (orchestration)
- **RAG**: ChromaDB (vector store), HuggingFace (embeddings)
- **Database**: PostgreSQL + TimescaleDB
- **Cache**: Redis

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **3D Graphics**: Three.js + React Three Fiber
- **Charts**: Recharts, Plotly.js
- **State**: Zustand
- **API Client**: Axios

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Orchestration**: Kubernetes (production)
- **Monitoring**: Prometheus + Grafana
- **Logging**: Loguru (structured logging)

## Data Flow

### 1. Ingestion
```python
Telemetry CSV → TelemetryIngestor → Validation → DataFrame
```

### 2. Processing
```python
Raw Data → Feature Extraction → Normalization → Model Input
```

### 3. Anomaly Detection
```python
Features → FCNN Forward Pass → Sigmoid → Probability → Binary Decision
```

### 4. Root Cause Analysis
```python
Anomalous Channels → KG Query → Fault Ranking → Top-K Root Causes
```

### 5. Explanation Generation
```python
Anomaly + Root Causes → RAG Retrieval → LLM Prompt → Explanation + Actions
```

### 6. Dashboard Display
```python
API Response → State Management → React Components → User Interface
```

## Performance Characteristics

- **Anomaly Detection Latency**: <50ms
- **Root Cause Analysis**: <100ms
- **LLM Explanation Generation**: <2s
- **End-to-End Pipeline**: <3s
- **Dashboard Update Frequency**: 1Hz (1 update/second)

## Scalability Considerations

1. **Horizontal Scaling**: FastAPI workers behind load balancer
2. **Model Serving**: Batched inference for throughput
3. **Caching**: Redis for frequent queries
4. **Database**: TimescaleDB for time-series optimization
5. **Message Queue**: Celery for async processing

## Security

- API authentication (JWT tokens)
- CORS configuration
- Rate limiting
- Input validation (Pydantic schemas)
- Secrets management (environment variables)

## Monitoring & Observability

- Structured logging (Loguru)
- Prometheus metrics
- Health check endpoints
- Model performance tracking
- Anomaly event logging
