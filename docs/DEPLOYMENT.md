# Deployment Guide

## Production Deployment

### Prerequisites

- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Ollama (for LLM)
- 4GB+ RAM
- 10GB+ disk space

---

## Option 1: Docker Compose (Recommended)

### 1. Setup Environment

```bash
# Clone repository
git clone <repository_url>
cd satellite-telemetry-diagnosis

# Create production environment file
cp backend/.env.example backend/.env

# Update .env with production values
nano backend/.env
```

### 2. Build and Start

```bash
# Build all services
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Pull LLM Model

```bash
# Connect to Ollama container
docker exec -it telemetry-ollama ollama pull llama3

# Verify
docker exec -it telemetry-ollama ollama list
```

### 4. Initialize Database

```bash
# Run migrations
docker exec -it telemetry-backend python scripts/init_db.py
```

### 5. Train Model

```bash
# Train FCNN model
docker exec -it telemetry-backend python scripts/train_fcnn.py
```

### 6. Access Services

- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

---

## Option 2: Manual Deployment

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Setup database
python scripts/init_db.py

# Train model
python scripts/train_fcnn.py

# Start API (production)
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Start production server
npm start
```

---

## Option 3: Kubernetes Deployment

### 1. Create Kubernetes Manifests

```bash
# Generate manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

### 2. Verify Deployment

```bash
# Check pods
kubectl get pods -n telemetry

# Check services
kubectl get svc -n telemetry

# View logs
kubectl logs -f deployment/backend -n telemetry
```

---

## Environment Variables (Production)

### Backend (.env)

```bash
# Application
APP_NAME="Satellite Telemetry Fault Diagnosis System"
ENVIRONMENT=production
DEBUG=False

# API
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/telemetry_db

# Redis
REDIS_URL=redis://redis:6379/0

# LLM
LLM_MODEL=llama3
LLM_API_BASE=http://ollama:11434
LLM_TEMPERATURE=0.1

# Security
SECRET_KEY=<generate-secure-key>
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=True
```

### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://api.yourdomain.com
NEXT_PUBLIC_WS_URL=ws://api.yourdomain.com/ws
```

---

## Performance Tuning

### Backend

1. **Gunicorn Workers:**
   ```bash
   # Formula: (2 x CPU cores) + 1
   gunicorn -w 9 -k uvicorn.workers.UvicornWorker src.api.main:app
   ```

2. **Database Connection Pool:**
   ```python
   DATABASE_POOL_SIZE=20
   DATABASE_MAX_OVERFLOW=10
   ```

3. **Redis Caching:**
   ```python
   CACHE_TTL=300  # 5 minutes
   ```

### Frontend

1. **Enable Static Generation:**
   ```typescript
   // next.config.js
   output: 'standalone'
   ```

2. **CDN for Assets:**
   Use CDN for static assets in production.

---

## Monitoring

### Prometheus Metrics

Backend exposes metrics at:
```
http://localhost:8000/metrics
```

### Logging

Logs are stored in:
- **Backend**: `backend/logs/`
- **Docker**: `docker-compose logs`

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database health
docker exec telemetry-db pg_isready

# Redis health
docker exec telemetry-redis redis-cli ping
```

---

## Backup & Recovery

### Database Backup

```bash
# Backup
docker exec telemetry-db pg_dump -U postgres telemetry_db > backup.sql

# Restore
docker exec -i telemetry-db psql -U postgres telemetry_db < backup.sql
```

### Model Backup

```bash
# Backup trained models
tar -czf models_backup.tar.gz backend/models/trained/

# Backup vector store
tar -czf vector_store_backup.tar.gz backend/vector_store/
```

---

## Security Checklist

- [ ] Update default passwords in `.env`
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Enable API authentication
- [ ] Set up rate limiting
- [ ] Regular security updates
- [ ] Backup sensitive data
- [ ] Enable audit logging

---

## Troubleshooting Production Issues

### High Memory Usage
- Reduce batch size in model inference
- Limit vector store cache size
- Optimize database queries

### Slow Response Times
- Enable Redis caching
- Use database query optimization
- Scale horizontally with load balancer

### Model Serving Errors
- Check model file integrity
- Verify GPU availability
- Review error logs

---

## Scaling Strategy

### Phase 1: Vertical Scaling (Single Server)
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 100GB SSD

### Phase 2: Horizontal Scaling (Multi-Server)
- Load balancer (Nginx)
- Multiple API workers
- Dedicated database server
- Redis cluster

### Phase 3: Microservices Architecture
- Separate anomaly detection service
- Dedicated KG reasoning service
- Independent LLM/RAG service
- Message queue (RabbitMQ/Kafka)
