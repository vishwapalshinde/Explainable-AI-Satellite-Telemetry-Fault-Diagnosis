# Explainable AI-based Satellite Telemetry Fault Diagnosis System

## 🛰️ Project Overview
Production-grade system for real-time satellite telemetry analysis, anomaly detection, authenticated operator access, and explainable fault diagnosis for the ESA OPS-SAT ADCS subsystem.

## 🏗️ Architecture

```
Telemetry Data → Ingestion → Processing → FCNN Anomaly Detection → Knowledge Graph RCA → LLM+RAG Explanation → Enterprise Dashboard
```

## ✅ Latest Update (May 2026)

This version includes the complete authentication, role-management, and dashboard stabilization work.

### Key Updates
- Sign-up and sign-in flow now normalize usernames and emails and auto-login after registration
- Role-aware dashboard navigation and access restrictions are enforced on both frontend and backend
- Settings button now opens the settings section instead of doing nothing
- Header layout was tightened so the title stays aligned and readable
- PostgreSQL is supported through Docker Compose, with SQLite fallback for local development
- A role-change utility script is now available for promoting users to engineer or admin

### System Components:
1. **Data Ingestion & Processing**: Deterministic telemetry replay from `segments.csv` and feature extraction into ML-ready vectors
2. **Anomaly Detection**: FCNN with dropout and batch normalization for structured telemetry features
3. **Root Cause Analysis**: Knowledge Graph mapping of ADCS subsystem relationships
4. **Explainability Layer**: LLM + RAG with timeout handling and deterministic fallback
5. **Enterprise Dashboard**: Next.js web interface with role-based navigation and settings

## 📊 Dataset
- **Source**: ESA OPS-SAT CubeSat Mission (AI-ready benchmark)
- **Subsystem**: ADCS (Attitude Determination and Control System)
- **Channels**: 9 total
  - 3 Magnetometer channels
  - 6 Photodiode channels
- **Files**:
  - `segments.csv`: Raw time-series telemetry data (303K+ records)
  - `dataset.csv`: Pre-computed segment features (2125 segments)

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+

### Installation
```bash
# Backend setup
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install

# Start all services
docker-compose up -d
```

## 📘 Main Project Guide

For the full end-to-end explanation of the architecture, data flow, ML pipeline, database design, reviewer questions, and viva defense notes, read [docs/PROJECT_EXAM_GUIDE.md](docs/PROJECT_EXAM_GUIDE.md).

## 📁 Project Structure
```
├── backend/           # Python backend services
├── frontend/          # React/Next.js dashboard
├── models/            # Trained ML models
├── knowledge_graph/   # KG schemas and data
├── dataset/           # ESA OPS-SAT telemetry data
├── docs/              # Documentation and exam guide
└── docker/            # Docker configurations
```

## 🛠️ Tech Stack

### Backend
- **API**: FastAPI + Pydantic v2
- **ML Framework**: PyTorch 2.0+
- **Anomaly Detection**: FCNN (primary), AdaBoost (baseline)
- **Knowledge Graph**: Neo4j / NetworkX
- **LLM/RAG**: LangChain + Ollama/vLLM + ChromaDB
- **Database**: PostgreSQL + TimescaleDB
- **Queue**: Redis

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **UI**: Tailwind CSS + shadcn/ui
- **Charts**: Recharts + Plotly.js
- **3D**: Three.js (satellite orientation)
- **State Management**: Zustand

## 📈 Performance Targets
- Anomaly Detection Accuracy: >90%
- Real-time Processing: <100ms latency
- Explanation Generation: <2s
- Dashboard Response: <50ms

## 📊 Evaluation Metrics
- Diagrams and metric summaries are available in [docs/EVALUATION_METRICS.md](docs/EVALUATION_METRICS.md)

## 🔐 Authentication And Roles

- Viewer accounts are created through the sign-up form.
- Engineer and admin accounts can be created or promoted with backend scripts.
- Database state depends on whether PostgreSQL is running; if not, the app uses SQLite for local development.

## 🗄️ Data And Database

- Raw telemetry replay currently comes from `dataset/segments.csv`.
- Feature-level training data is available in `dataset/dataset.csv`.
- Runtime persistence uses PostgreSQL when Docker is available, otherwise SQLite fallback.
- You can inspect user and telemetry records directly from the database, depending on the active runtime.

## 🔬 Research Alignment
Built for production deployment AND academic research publication.

## 📝 License
MIT License

## 👥 Contributing
This is a research project aimed at solving real aerospace problems.
