"""
Configuration Management for Satellite Telemetry Fault Diagnosis System
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "Satellite Telemetry Fault Diagnosis System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="development")
    
    # API
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_PREFIX: str = Field(default="/api/v1")
    CORS_ORIGINS: list = Field(default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ])
    
    # Database
    DATABASE_URL: str = Field(default="postgresql://postgres:postgres@localhost:5432/telemetry_db")
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=10)
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CACHE_TTL: int = Field(default=300)  # 5 minutes
    
    # Model Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "dataset"
    MODELS_DIR: Path = BASE_DIR / "models"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Dataset Configuration
    DATASET_CSV: str = "dataset.csv"
    SEGMENTS_CSV: str = "segments.csv"
    
    # ADCS Channels
    MAGNETOMETER_CHANNELS: list = Field(default=["CADC0872", "CADC0873", "CADC0874"])
    PHOTODIODE_CHANNELS: list = Field(default=["CADC0875", "CADC0876", "CADC0877", "CADC0878", "CADC0879", "CADC0880"])
    
    # FCNN Model Configuration
    FCNN_HIDDEN_LAYERS: list = Field(default=[128, 64, 32])
    FCNN_DROPOUT_RATE: float = Field(default=0.3)
    FCNN_BATCH_SIZE: int = Field(default=32)
    FCNN_LEARNING_RATE: float = Field(default=0.001)
    FCNN_EPOCHS: int = Field(default=100)
    FCNN_EARLY_STOPPING_PATIENCE: int = Field(default=10)
    
    # AdaBoost Baseline Configuration
    ADABOOST_N_ESTIMATORS: int = Field(default=100)
    ADABOOST_LEARNING_RATE: float = Field(default=1.0)
    
    # Anomaly Detection Thresholds
    ANOMALY_CONFIDENCE_THRESHOLD: float = Field(default=0.7)
    ALERT_SEVERITY_LEVELS: dict = Field(default={
        "critical": 0.9,
        "high": 0.75,
        "medium": 0.5,
        "low": 0.3
    })
    
    # Knowledge Graph Configuration
    KG_NEO4J_URI: Optional[str] = Field(default=None)
    KG_NEO4J_USER: Optional[str] = Field(default="neo4j")
    KG_NEO4J_PASSWORD: Optional[str] = Field(default="password")
    KG_USE_NETWORKX: bool = Field(default=True)  # Fallback to NetworkX if Neo4j not available
    
    # LLM Configuration
    LLM_PROVIDER: str = Field(default="ollama")  # ollama, vllm, openai
    LLM_MODEL: str = Field(default="llama3.1:latest")
    LLM_API_BASE: str = Field(default="http://127.0.0.1:11434")
    LLM_TEMPERATURE: float = Field(default=0.1)
    LLM_MAX_TOKENS: int = Field(default=1000)
    
    # RAG Configuration
    RAG_VECTOR_STORE: str = Field(default="chromadb")  # chromadb, faiss
    RAG_EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    RAG_CHUNK_SIZE: int = Field(default=1000)
    RAG_CHUNK_OVERLAP: int = Field(default=200)
    RAG_TOP_K_RESULTS: int = Field(default=5)
    
    # Monitoring
    ENABLE_METRICS: bool = Field(default=True)
    ENABLE_TRACING: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Create necessary directories
def setup_directories():
    """Create required directories if they don't exist"""
    dirs = [
        settings.MODELS_DIR,
        settings.MODELS_DIR / "trained",
        settings.MODELS_DIR / "checkpoints",
        settings.LOGS_DIR,
        settings.BASE_DIR / "data" / "processed",
        settings.BASE_DIR / "data" / "cache",
        settings.BASE_DIR / "knowledge_graph" / "exports",
        settings.BASE_DIR / "vector_store",
    ]
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    setup_directories()
    print(f"✅ Configuration loaded for {settings.ENVIRONMENT} environment")
    print(f"📂 Data directory: {settings.DATA_DIR}")
    print(f"🤖 Models directory: {settings.MODELS_DIR}")
