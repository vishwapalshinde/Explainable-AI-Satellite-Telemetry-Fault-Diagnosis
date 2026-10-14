# Development Guide

## Getting Started

### 1. Initial Setup

#### Windows:
```bash
# Run setup script
scripts\setup.bat
```

#### Linux/Mac:
```bash
# Make script executable
chmod +x scripts/setup.sh

# Run setup
./scripts/setup.sh
```

### 2. Environment Configuration

Copy the environment template and configure:
```bash
cp backend/.env.example backend/.env
```

Update the following variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `LLM_API_BASE`: Ollama API endpoint

### 3. Install Ollama (for LLM explanations)

**Windows:**
1. Download from https://ollama.ai/download/windows
2. Install and run
3. Pull model: `ollama pull llama3`

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3
```

### 4. Train the Model

```bash
cd backend
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

python scripts/train_fcnn.py
```

Expected output:
- Trained model saved to `models/trained/fcnn_anomaly_detector.pt`
- Training metrics and plots in `models/experiments/`
- Target accuracy: >90%

### 5. Start Development Servers

**Terminal 1 - Backend API:**
```bash
cd backend
venv\Scripts\activate
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend Dashboard:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Ollama (if not running as service):**
```bash
ollama serve
```

### 6. Access the Dashboard

Open browser: http://localhost:3000

API documentation: http://localhost:8000/docs

## Development Workflow

## Recent Runtime Changes (April 2026)

### Telemetry Replay
- Replay is sourced from raw `dataset/segments.csv` snapshots.
- Cursor state is persisted at `data/cache/replay_state.json`.
- On restart, replay resumes from the saved cursor instead of always starting at segment 0.

### Diagnosis Chat
- Frontend chat history is persisted in browser local storage.
- Backend keeps short session context for follow-up questions.
- Chat timeout is configurable using environment variable:

```bash
CHAT_RESPONSE_TIMEOUT_SECONDS=60
```

If Ollama takes longer than this timeout, backend returns a deterministic fallback response to keep the UI responsive.

### RAG Pipeline
- New ADCS manuals and operational PDFs in `docs/` are prioritized for retrieval.
- Section-aware source labels are used for better traceability in responses.
- Vector store is cached and reused when KB content hash is unchanged.
- Re-embedding is triggered only when source documents change.

### Adding New Features

1. **Backend Feature:**
   - Create feature module in `backend/src/`
   - Add tests in `backend/tests/`
   - Update API routes in `backend/src/api/`
   - Document in docstrings

2. **Frontend Feature:**
   - Create component in `frontend/src/components/`
   - Update state management in `frontend/src/store/`
   - Add types in TypeScript interfaces
   - Style with Tailwind CSS

### Testing

**Backend:**
```bash
cd backend
pytest tests/ -v --cov=src
```

**Frontend:**
```bash
cd frontend
npm run test
npm run type-check
```

### Code Quality

**Python (Backend):**
```bash
# Format
black src/

# Lint
flake8 src/

# Type check
mypy src/
```

**TypeScript (Frontend):**
```bash
# Lint
npm run lint

# Type check
npm run type-check
```

## Project Structure Deep Dive

### Backend Structure
```
backend/
├── src/
│   ├── api/              # FastAPI routes and middleware
│   ├── ingestion/        # Data loading and validation
│   ├── processing/       # Feature engineering and scaling
│   ├── models/           # ML models (FCNN, AdaBoost)
│   ├── knowledge_graph/  # KG builder and reasoning
│   ├── explainability/   # LLM + RAG explanation
│   ├── utils/            # Logger, config, helpers
│   └── config.py         # Central configuration
├── scripts/              # Training and utility scripts
└── tests/                # Unit and integration tests
```

### Frontend Structure
```
frontend/
├── src/
│   ├── app/              # Next.js app router pages
│   ├── components/       # React components
│   ├── store/            # Zustand state management
│   └── lib/              # Utility functions
└── public/               # Static assets
```

## Common Tasks

### Update Dataset
```bash
# Place new CSV files in dataset/ folder
# Re-run training:
cd backend
python scripts/train_fcnn.py
```

### Rebuild Knowledge Graph
```bash
cd backend
python -c "
from src.knowledge_graph import ADCSKnowledgeGraph
kg = ADCSKnowledgeGraph()
kg.build_adcs_ontology()
kg.export_to_json('knowledge_graph/adcs_kg.json')
"
```

### Update RAG Knowledge Base
Edit: `backend/src/explainability/diagnosis_explainer.py`
Function: `create_knowledge_base_documents()`

After adding/removing KB files:
1. Restart backend
2. First startup rebuilds embeddings and vector store
3. Subsequent startups reuse cached vector store automatically

### View Model Performance
```bash
# Check experiment results
ls backend/models/experiments/

# View training plots
# Open PNG files in models/experiments/<experiment_name>/evaluation/
```

## Docker Development

### Build and run all services:
```bash
docker-compose up --build
```

### Run specific service:
```bash
docker-compose up backend
docker-compose up frontend
```

### View logs:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (need 3.10+)
- Activate venv: `venv\Scripts\activate`
- Check dependencies: `pip list`
- Check logs: `backend/logs/`

### Frontend won't start
- Check Node version: `node --version` (need 18+)
- Clear cache: `rm -rf .next/ && npm run dev`
- Check dependencies: `npm list`

### Model training fails
- Check dataset paths in `backend/src/config.py`
- Verify CSV files exist: `dataset/dataset.csv`, `dataset/segments.csv`
- Check GPU: `python -c "import torch; print(torch.cuda.is_available())"`

### LLM not generating explanations
- Verify Ollama is running: `http://localhost:11434`
- Check model is pulled: `ollama list`
- Review LLM config in `.env`

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [LangChain Documentation](https://python.langchain.com/)
- [ESA OPS-SAT Dataset Paper](https://github.com/esa/opssat-anomaly-detection)
