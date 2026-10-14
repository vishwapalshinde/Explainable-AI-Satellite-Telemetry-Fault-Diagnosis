"""
FastAPI Main Application
Production-grade REST API for Satellite Telemetry Fault Diagnosis System
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import os
from typing import List, Dict, Optional
import math
import torch
import numpy as np
import pandas as pd
from datetime import datetime

from ..config import settings, setup_directories
from ..utils.logger import LoggerSetup, get_logger
from ..database import get_db, User, create_all_tables, health_check as db_health_check
from .auth import router as auth_router
from .rbac import require_auth, require_permission
from ..ingestion import TelemetryIngestor
from ..processing import TelemetryProcessor
from ..models import FCNN, FCNNTrainer
from ..models.anomaly_detector import CharacteristicsExtractor
from ..knowledge_graph import ADCSKnowledgeGraph
from ..streaming import TelemetryReplayEngine

# Try to import explainability module (optional, may fail if LangChain has issues)
try:
    from ..explainability import DiagnosisExplainer, create_knowledge_base_documents
    EXPLAINABILITY_AVAILABLE = True
except Exception as e:
    EXPLAINABILITY_AVAILABLE = False
    DiagnosisExplainer = None
    create_knowledge_base_documents = None
    print(f"Warning: Explainability module unavailable: {e}")

# Initialize logger
setup_directories()
LoggerSetup.setup(settings.LOGS_DIR, level=settings.LOG_LEVEL)
logger = get_logger()

# Global state
app_state = {
    'model': None,
    'processor': None,
    'kg': None,
    'explainer': None,
    'replay_engine': None,
    'model_metadata': {},
    'anomaly_threshold': 0.5,
    'dataset_df': None,
    'dataset_indices': {},
    'dataset_positions': {},
    'chat_sessions': {}
}

DEFAULT_ANOMALY_THRESHOLD = 0.5
CHAT_RESPONSE_TIMEOUT_SECONDS = int(os.getenv("CHAT_RESPONSE_TIMEOUT_SECONDS", "240"))


def sanitize_nan(value):
    """Convert NaN values to None for JSON serialization"""
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    return value


def get_feature_columns() -> List[str]:
    """Return processor feature columns with a stable fallback order."""
    processor = app_state.get('processor')
    if processor is not None and getattr(processor, 'feature_columns', None):
        return list(processor.feature_columns)

    return [
        'duration', 'len', 'mean', 'var', 'std', 'kurtosis', 'skew',
        'n_peaks', 'smooth10_n_peaks', 'smooth20_n_peaks', 'diff_peaks',
        'diff2_peaks', 'diff_var', 'diff2_var', 'gaps_squared',
        'len_weighted', 'var_div_duration', 'var_div_len'
    ]


def build_feature_dict(row: pd.Series, feature_columns: List[str]) -> Dict[str, float]:
    """Build a numeric feature payload from a dataset row."""
    features: Dict[str, float] = {}
    for col in feature_columns:
        raw_value = row.get(col, 0.0)
        try:
            features[col] = float(raw_value)
        except (TypeError, ValueError):
            features[col] = 0.0
    return features


def root_cause_fault_id(root_cause) -> str:
    """Extract fault identifier from KG output (dict or tuple/list)."""
    if isinstance(root_cause, dict):
        return str(
            root_cause.get('fault_id')
            or root_cause.get('fault_name')
            or root_cause.get('fault')
            or 'unknown_fault'
        )
    if isinstance(root_cause, (list, tuple)) and root_cause:
        return str(root_cause[0])
    return 'unknown_fault'


def root_cause_confidence(root_cause) -> float:
    """Extract confidence score from KG output (dict or tuple/list)."""
    if isinstance(root_cause, dict):
        return float(root_cause.get('confidence', 0.0) or 0.0)
    if isinstance(root_cause, (list, tuple)) and len(root_cause) > 1:
        try:
            return float(root_cause[1])
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def serialize_root_causes(root_causes: List) -> List[Dict]:
    """Convert KG root-cause output into API response structure."""
    results = []
    for rc in root_causes:
        if isinstance(rc, dict):
            results.append({
                "fault": root_cause_fault_id(rc),
                "confidence": root_cause_confidence(rc),
                "description": rc.get('description', ''),
                "severity": rc.get('severity', 'unknown'),
                "fault_name": rc.get('fault_name', root_cause_fault_id(rc))
            })
        else:
            results.append({
                "fault": root_cause_fault_id(rc),
                "confidence": root_cause_confidence(rc)
            })
    return results


def extract_characteristics_from_features(features: Dict[str, float]) -> List[str]:
    """Derive observable anomaly characteristics from ML features."""
    try:
        return CharacteristicsExtractor.extract_characteristics(features)
    except Exception:
        return []


def build_evidence_summary(probability: float, affected_channels: List[str], root_causes: List[Dict], characteristics: List[str]) -> Dict:
    """Build a compact evidence summary for diagnosis responses."""
    return {
        "anomaly_probability": float(probability),
        "affected_channels": affected_channels,
        "characteristics": characteristics,
        "probable_root_causes": [
            {
                "fault_id": rc.get('fault_id') or rc.get('fault') or rc.get('fault_name', 'unknown_fault'),
                "fault_name": rc.get('fault_name') or rc.get('fault', 'unknown_fault'),
                "confidence": float(rc.get('confidence', 0.0) or 0.0)
            }
            for rc in root_causes[:5]
        ]
    }


def get_anomaly_threshold() -> float:
    """Return the trained anomaly threshold when available."""
    threshold = app_state.get('anomaly_threshold', DEFAULT_ANOMALY_THRESHOLD)
    try:
        return float(threshold)
    except (TypeError, ValueError):
        return DEFAULT_ANOMALY_THRESHOLD


def get_next_dataset_row(channel: str) -> Optional[pd.Series]:
    """Get next dataset row for a channel in round-robin order."""
    indices = app_state.get('dataset_indices', {}).get(channel, [])
    if not indices:
        return None

    positions = app_state.get('dataset_positions', {})
    pos = positions.get(channel, 0)
    idx = indices[pos % len(indices)]
    positions[channel] = (pos + 1) % len(indices)
    app_state['dataset_positions'] = positions

    df = app_state.get('dataset_df')
    if df is None:
        return None
    return df.iloc[idx]


def infer_anomaly(features: Dict[str, float], timestamp: Optional[str] = None) -> Dict:
    """Run model inference for one feature vector and return normalized anomaly fields."""
    X_scaled = app_state['processor'].transform(
        pd.DataFrame([features], columns=app_state['processor'].feature_columns)
    )

    with torch.no_grad():
        X_tensor = torch.FloatTensor(X_scaled)
        probability = app_state['model'].predict_proba(X_tensor).item()

    detected = bool(probability >= get_anomaly_threshold())
    severity = "HIGH" if probability >= 0.75 else "MEDIUM" if probability >= 0.5 else "LOW"
    characteristics = extract_characteristics_from_features(features)

    return {
        "detected": detected,
        "anomaly_detected": detected,
        "probability": float(probability),
        "severity": severity,
        "timestamp": timestamp or datetime.now().isoformat(),
        "characteristics": characteristics
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting Satellite Telemetry Fault Diagnosis API")
    
    try:
        # Initialize database (create tables if they don't exist)
        logger.info("📦 Initializing database...")
        try:
            create_all_tables()
            logger.info("✅ Database tables created/verified")
        except Exception as db_error:
            logger.warning(f"⚠️ Database initialization warning: {db_error}")
        
        # Load trained model
        model_path = settings.MODELS_DIR / "trained" / "fcnn_anomaly_detector.pt"
        if model_path.exists():
            model, trainer = FCNNTrainer.load_model(model_path)
            model.eval()
            app_state['model'] = model
            app_state['model_metadata'] = getattr(trainer, 'metadata', {}) or {}
            app_state['anomaly_threshold'] = float(
                app_state['model_metadata'].get('threshold', DEFAULT_ANOMALY_THRESHOLD)
            )
            logger.info("✅ FCNN model loaded")
            logger.info(f"✅ Anomaly threshold set to {app_state['anomaly_threshold']:.2f}")
        else:
            logger.warning("⚠️  No trained model found. API running in limited mode.")
        
        # Load data processor
        processor_path = settings.MODELS_DIR / "trained" / "data_processor.pkl"
        if processor_path.exists():
            app_state['processor'] = TelemetryProcessor.load(processor_path)
            logger.info("✅ Data processor loaded")
        
        # Initialize Knowledge Graph
        kg = ADCSKnowledgeGraph()
        kg.build_adcs_ontology()
        app_state['kg'] = kg
        logger.info("✅ Knowledge Graph initialized")
        
        # Initialize RAG Explainer (optional)
        if EXPLAINABILITY_AVAILABLE:
            try:
                explainer = DiagnosisExplainer()
                app_state['explainer'] = explainer

                try:
                    documents = create_knowledge_base_documents()
                    explainer.load_knowledge_base(documents)
                    explainer.initialize_qa_chain()
                    logger.info("✅ RAG Explainer initialized")
                except Exception as e:
                    logger.warning(f"⚠️ RAG knowledge base initialization failed: {e}. Chat/explanations will run with reduced capabilities.")

            except Exception as e:
                logger.warning(f"⚠️  RAG initialization failed: {e}. Running without LLM explanations.")
        else:
            logger.warning("⚠️  Explainability module unavailable. Running without LLM explanations.")

        # Load dataset for near real-time telemetry playback
        dataset_path = settings.DATA_DIR / settings.DATASET_CSV
        if dataset_path.exists():
            try:
                dataset_df = pd.read_csv(dataset_path)
                if 'channel' not in dataset_df.columns:
                    raise ValueError("dataset.csv missing required 'channel' column")

                dataset_df = dataset_df.reset_index(drop=True)
                dataset_indices: Dict[str, List[int]] = {}
                dataset_positions: Dict[str, int] = {}

                for channel in sorted(dataset_df['channel'].dropna().unique()):
                    channel_rows = dataset_df.index[dataset_df['channel'] == channel].tolist()
                    if channel_rows:
                        dataset_indices[str(channel)] = channel_rows
                        dataset_positions[str(channel)] = 0

                app_state['dataset_df'] = dataset_df
                app_state['dataset_indices'] = dataset_indices
                app_state['dataset_positions'] = dataset_positions

                logger.info(
                    f"✅ Dataset loaded for telemetry playback: {len(dataset_df)} rows across "
                    f"{len(dataset_indices)} channels"
                )
            except Exception as e:
                logger.warning(f"⚠️ Dataset preload failed: {e}")
        else:
            logger.warning(f"⚠️ Dataset file not found: {dataset_path}")

        # Load raw segment replay engine for near real-time telemetry simulation
        segments_path = settings.DATA_DIR / settings.SEGMENTS_CSV
        if segments_path.exists():
            try:
                app_state['replay_engine'] = TelemetryReplayEngine(segments_path)
                logger.info("✅ Raw telemetry replay engine initialized")
            except Exception as e:
                logger.warning(f"⚠️ Replay engine initialization failed: {e}")
        else:
            logger.warning(f"⚠️ Raw segments file not found: {segments_path}")
        
        logger.info("✅ API startup complete")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🔻 Shutting down API")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade API for satellite telemetry anomaly detection and fault diagnosis",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)


# ============================================================================
# API ROUTES
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "models_loaded": app_state['model'] is not None,
        "kg_loaded": app_state['kg'] is not None,
        "rag_loaded": app_state['explainer'] is not None
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    explainer = app_state.get('explainer')
    rag_ready = bool(
        explainer is not None
        and getattr(explainer, 'ollama_available', False)
        and getattr(explainer, 'vector_store', None) is not None
    )

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "fcnn_model": app_state['model'] is not None,
            "data_processor": app_state['processor'] is not None,
            "knowledge_graph": app_state['kg'] is not None,
            "rag_explainer": rag_ready,
            "telemetry_replay": app_state['replay_engine'] is not None,
            "xai_fallback_available": explainer is not None
        }
    }


@app.post("/api/v1/detect")
async def detect_anomaly(request: Dict):
    """
    Detect anomaly in telemetry data
    
    Request body:
    {
        "features": {...},  # Feature values
        "channel": "CADC0872",
        "timestamp": "2024-01-01T00:00:00Z"
    }
    
    Returns anomaly probability and prediction
    """
    if app_state['model'] is None or app_state['processor'] is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        features = request.get('features', {})
        channel = request.get('channel', 'unknown')
        timestamp = request.get('timestamp', datetime.now().isoformat())
        
        detection = infer_anomaly(features, timestamp=timestamp)
        
        result = {
            **detection,
            "channel": channel,
        }
        
        logger.bind(anomaly=True).info(
            f"Anomaly detection: Channel={channel}, Prob={detection['probability']:.2%}, Detected={detection['detected']}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/diagnose")
async def diagnose_fault(request: Dict):
    """
    Complete fault diagnosis pipeline
    
    Request body:
    {
        "features": {...},
        "channels": ["CADC0872", "CADC0873"],
        "timestamp": "2024-01-01T00:00:00Z"
    }
    
    Returns comprehensive diagnosis with root causes and explanations
    """
    if app_state['model'] is None or app_state['kg'] is None:
        raise HTTPException(status_code=503, detail="System components not loaded")
    
    try:
        features = request.get('features', {})
        channels = request.get('channels', [])
        timestamp = request.get('timestamp', datetime.now().isoformat())
        
        # Step 1: Anomaly Detection
        detection = infer_anomaly(features, timestamp=timestamp)
        
        anomaly_summary = {
            "probability": detection['probability'],
            "detected": detection['detected'],
            "timestamp": timestamp,
            "severity": detection['severity'],
            "characteristics": detection['characteristics']
        }
        
        # Step 2: Knowledge Graph Root Cause Analysis
        root_causes = []
        if anomaly_summary['detected'] and channels:
            root_causes = app_state['kg'].find_root_causes(
                channels,
                anomaly_probability=float(anomaly_summary['probability']),
                severity=anomaly_summary['severity'],
                characteristics=anomaly_summary['characteristics'],
                top_k=5
            )
        
        # Step 3: LLM+RAG Explanation
        explanation_result = {}
        if app_state['explainer'] and anomaly_summary['detected']:
            explanation_result = app_state['explainer'].generate_explanation(
                anomaly_summary=anomaly_summary,
                root_causes=root_causes,
                affected_channels=channels
            )

        if anomaly_summary['detected'] and not explanation_result:
            top_faults = [root_cause_fault_id(rc) for rc in root_causes[:3]]
            explanation_result = {
                "explanation": (
                    "Anomaly detected in ADCS telemetry. "
                    + (f"Most probable causes: {', '.join(top_faults)}." if top_faults else "Root causes are being investigated.")
                ),
                "severity": anomaly_summary['severity'],
                "corrective_actions": [
                    "Validate magnetometer calibration and sensor health",
                    "Inspect ADCS control loop gains and reaction wheel behavior",
                    "Increase telemetry sampling and continue monitoring"
                ],
                "confidence": float(anomaly_summary['probability']),
                "explanation_mode": "rule_based_fallback",
                "source_references": ["KG rules", "ADCS fallback playbook"],
                "evidence_summary": build_evidence_summary(
                    float(anomaly_summary['probability']),
                    channels,
                    root_causes,
                    anomaly_summary['characteristics']
                )
            }
        elif not anomaly_summary['detected']:
            explanation_result = {
                "explanation": "No anomaly detected. ADCS telemetry remains within nominal operating bounds.",
                "severity": "LOW",
                "corrective_actions": [
                    "Continue routine telemetry monitoring",
                    "Keep scheduled health checks for ADCS sensors"
                ],
                "confidence": float(1.0 - anomaly_summary['probability']),
                "explanation_mode": "nominal",
                "source_references": ["Nominal operating envelope"],
                "evidence_summary": build_evidence_summary(
                    float(anomaly_summary['probability']),
                    channels,
                    [],
                    anomaly_summary['characteristics']
                )
            }
        
        # Build response
        result = {
            "timestamp": timestamp,
            "anomaly_detection": anomaly_summary,
            "affected_channels": channels,
            "root_causes": [
                rc
                for rc in serialize_root_causes(root_causes)
            ],
            "diagnosis": {
                "explanation": explanation_result.get('explanation', 'No explanation available'),
                "severity": explanation_result.get('severity', 'UNKNOWN'),
                "corrective_actions": explanation_result.get('corrective_actions', []),
                "confidence": explanation_result.get('confidence', 0.0),
                "explanation_mode": explanation_result.get('explanation_mode', 'unknown'),
                "source_references": explanation_result.get('source_references', []),
                "evidence_summary": explanation_result.get(
                    'evidence_summary',
                    build_evidence_summary(
                        float(anomaly_summary['probability']),
                        channels,
                        root_causes,
                        anomaly_summary['characteristics']
                    )
                )
            }
        }
        
        logger.bind(anomaly=True).info(
            f"Fault diagnosis completed: Channels={channels}, Severity={result['diagnosis']['severity']}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Diagnosis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/telemetry/next")
async def get_next_telemetry_snapshot(
    include_all_channels: bool = Query(default=False),
    include_llm_explanation: bool = Query(default=False)
):
    """Return the next near real-time telemetry snapshot sourced from segments.csv."""
    if app_state['model'] is None or app_state['processor'] is None:
        raise HTTPException(status_code=503, detail="Model components not loaded")

    if app_state.get('replay_engine') is None:
        raise HTTPException(status_code=503, detail="Telemetry replay engine not loaded")

    try:
        payload = app_state['replay_engine'].next_snapshot(include_all_channels=include_all_channels)
        telemetry_rows = payload.get('channels', [])
        if not telemetry_rows:
            raise HTTPException(status_code=404, detail="No telemetry rows available")

        channel_detections: Dict[str, Dict] = {}
        for row in telemetry_rows:
            channel_detections[row['channel']] = infer_anomaly(row.get('features', {}))

        # Treat magnetometer channels as primary anomaly trigger path.
        magnetometer_detected = {
            ch: det for ch, det in channel_detections.items()
            if ch in settings.MAGNETOMETER_CHANNELS and det.get('detected')
        }
        primary_detected = magnetometer_detected or {
            ch: det for ch, det in channel_detections.items() if det.get('detected')
        }

        active_channels = [row['channel'] for row in telemetry_rows]
        anomalous_channels = list(primary_detected.keys())

        primary_channel = None
        if anomalous_channels:
            primary_channel = max(anomalous_channels, key=lambda ch: channel_detections[ch]['probability'])
        else:
            primary_channel = max(channel_detections.keys(), key=lambda ch: channel_detections[ch]['probability'])

        primary = next((r for r in telemetry_rows if r['channel'] == primary_channel), telemetry_rows[0])
        primary_detection = channel_detections[primary_channel]
        detected = bool(len(anomalous_channels) > 0)
        severity = primary_detection['severity']
        characteristics = primary_detection['characteristics']

        root_causes = []
        if detected and app_state['kg'] is not None:
            root_causes = app_state['kg'].find_root_causes(
                anomalous_channels,
                anomaly_probability=float(primary_detection['probability']),
                severity=severity,
                characteristics=characteristics,
                top_k=5
            )

        diagnosis = None

        if detected:
            if include_llm_explanation and app_state['explainer'] is not None:
                try:
                    diagnosis = app_state['explainer'].generate_explanation(
                        anomaly_summary={
                            "probability": float(primary_detection['probability']),
                            "detected": detected,
                            "severity": severity,
                            "characteristics": characteristics,
                            "timestamp": payload.get('timestamp')
                        },
                        root_causes=root_causes,
                        affected_channels=anomalous_channels
                    )
                except Exception as e:
                    logger.warning(f"RAG explanation failed during telemetry snapshot: {e}")

            if not diagnosis or not diagnosis.get('explanation'):
                top_faults = [root_cause_fault_id(rc) for rc in root_causes[:3]]
                diagnosis = {
                    "explanation": (
                        "Anomaly detected from live dataset playback. "
                        + (f"Most probable causes: {', '.join(top_faults)}." if top_faults else "Root cause analysis is in progress.")
                    ),
                    "severity": severity,
                    "corrective_actions": [
                        "Inspect ADCS sensor calibration and sensor drift.",
                        "Check actuator response and control loop stability.",
                        "Increase monitoring cadence and validate related channels."
                    ],
                    "confidence": float(primary_detection['probability']),
                    "explanation_mode": "rule_based_fallback",
                    "source_references": ["KG rules", "ADCS fallback playbook"],
                    "evidence_summary": build_evidence_summary(
                        float(primary_detection['probability']),
                        active_channels,
                        root_causes,
                        characteristics
                    )
                }
        else:
            diagnosis = {
                "explanation": "No anomaly detected in current telemetry snapshot.",
                "severity": "LOW",
                "corrective_actions": ["Continue monitoring real-time ADCS telemetry."],
                "confidence": float(1.0 - primary_detection['probability']),
                "explanation_mode": "nominal",
                "source_references": ["Nominal operating envelope"],
                "evidence_summary": build_evidence_summary(
                    float(primary_detection['probability']),
                    active_channels,
                    [],
                    characteristics
                )
            }

        now_iso = datetime.now().isoformat()
        return {
            "timestamp": now_iso,
            "source": payload.get('source', 'segments.csv'),
            "mode": payload.get('mode', 'magnetometer_only'),
            "sampled_segment": primary['segment'],
            "channels": telemetry_rows,
            "current_features": primary.get('features', {}),
            "anomaly_detection": {
                "detected": detected,
                "anomaly_detected": detected,
                "probability": float(primary_detection['probability']),
                "severity": severity,
                "channel": primary_channel,
                "timestamp": now_iso,
                "dataset_anomaly": bool(primary.get('dataset_anomaly', False)),
                "characteristics": characteristics
            },
            "channel_detections": {
                channel: {
                    **det,
                    "dataset_anomaly": bool(next((row.get('dataset_anomaly', False) for row in telemetry_rows if row['channel'] == channel), False))
                }
                for channel, det in channel_detections.items()
            },
            "affected_channels": anomalous_channels,
            "root_causes": [
                rc
                for rc in serialize_root_causes(root_causes)
            ],
            "diagnosis": {
                "explanation": diagnosis.get('explanation', ''),
                "severity": diagnosis.get('severity', severity),
                "corrective_actions": diagnosis.get('corrective_actions', []),
                "confidence": float(
                    diagnosis.get(
                        'confidence',
                        primary_detection['probability'] if detected else (1.0 - primary_detection['probability'])
                    )
                ),
                "explanation_mode": diagnosis.get('explanation_mode', 'unknown'),
                "source_references": diagnosis.get('source_references', []),
                "evidence_summary": diagnosis.get(
                    'evidence_summary',
                    build_evidence_summary(
                        float(primary_detection['probability']),
                        active_channels,
                        root_causes,
                        characteristics
                    )
                )
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Telemetry snapshot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/knowledge-graph/nodes")
async def get_kg_nodes():
    """Get all knowledge graph nodes"""
    if app_state['kg'] is None:
        raise HTTPException(status_code=503, detail="Knowledge graph not loaded")
    
    nodes = [
        {
            "id": node_id,
            "type": node.type,
            "name": node.name,
            "description": node.description
        }
        for node_id, node in app_state['kg'].nodes.items()
    ]
    
    return {"nodes": nodes}


@app.post("/api/v1/test/inject-anomaly")
async def inject_test_anomaly(request: Optional[Dict] = None):
    """
    Manual anomaly injection for testing the complete diagnosis pipeline
    
    Request body (optional):
    {
        "anomaly_type": "magnetometer_bias",  // Optional: Type of anomaly to inject
        "severity": "high",  // Optional: "low", "medium", "high"
        "channels": ["CADC0872", "CADC0873", "CADC0874"]  // Optional: Specific channels
    }
    
    Returns complete diagnosis workflow: Detection → KG RCA → LLM Explanation
    """
    if app_state['model'] is None or app_state['processor'] is None or app_state['kg'] is None:
        raise HTTPException(status_code=503, detail="System components not loaded")
    
    try:
        # Parse request parameters
        request = request or {}
        anomaly_type = request.get('anomaly_type', 'magnetometer_bias')
        severity = request.get('severity', 'high').lower()
        channels = request.get('channels', ['CADC0872', 'CADC0873', 'CADC0874'])
        
        logger.info(f"🧪 Injecting test anomaly: type={anomaly_type}, severity={severity}")
        
        # Generate synthetic anomalous telemetry data using actual dataset features
        # Baseline values from normal samples in dataset (all 18 features in correct order)
        features = {
            'duration': 223.0,  # Average duration from dataset
            'len': 224.0,       # Average length from dataset
            'mean': 0.127,
            'var': 0.036,
            'std': 0.109,
            'kurtosis': -1.204,
            'skew': 0.178,
            'n_peaks': 1.33,
            'smooth10_n_peaks': 1.00,
            'smooth20_n_peaks': 1.15,
            'diff_peaks': 20.4,
            'diff2_peaks': 28.0,
            'diff_var': 0.00069,
            'diff2_var': 0.00017,
            'gaps_squared': 911.0,
            'len_weighted': 255.0,
            'var_div_duration': 0.000135,
            'var_div_len': 0.000493
        }
        
        # Inject anomaly to shift towards anomalous distribution
        # Based on actual anomalous samples: lower mean, lower var/std, higher n_peaks, etc.
        if anomaly_type == 'magnetometer_bias':
            # Simulate magnetometer bias drift (reduced mean, different variance pattern)
            features['mean'] *= 0.38  # Anomalies have much lower mean (0.048 vs 0.127)
            features['var'] *= 0.29   # Much lower variance 
            features['std'] *= 0.42   # Lower std
            features['kurtosis'] *= 0.52  # Less negative kurtosis
            features['n_peaks'] *= 1.77  # More peaks
            features['smooth10_n_peaks'] *= 1.52
            features['smooth20_n_peaks'] *= 1.12
            features['diff_peaks'] *= 0.45  # Anomalies have lower diff_peaks
            features['diff2_peaks'] *= 0.53
            features['diff_var'] *= 2.65
            features['diff2_var'] *= 26.5  # Much higher
            features['gaps_squared'] *= 1.47
            features['len_weighted'] *= 1.25
            features['var_div_duration'] *= 0.36
            features['var_div_len'] *= 0.43
            
        elif anomaly_type == 'sensor_noise':
            # Simulate increased sensor noise pattern
            features['var'] *= 2.5
            features['std'] *= 1.6
            features['diff_var'] *= 3.0
            features['diff2_var'] *= 26.0  # Big jump like in anomalies
            features['n_peaks'] *= 1.5
            features['smooth10_n_peaks'] *= 1.3
            
        elif anomaly_type == 'sudden_spike':
            # Simulate sudden spike/transient
            features['n_peaks'] *= 2.0
            features['diff_peaks'] *= 0.45  # Anomalies have lower diff_peaks
            features['diff2_peaks'] *= 0.53  # Lower diff2_peaks
            features['gaps_squared'] *= 1.48
            features['len_weighted'] *= 1.25
            features['mean'] *= 0.5
            
        elif anomaly_type == 'sensor_degradation':
            # Simulate gradual sensor degradation
            features['mean'] *= 0.4
            features['var'] *= 0.3
            features['std'] *= 0.4
            features['diff_peaks'] *= 0.5
            features['diff2_peaks'] *= 0.5
            features['var_div_duration'] *= 0.4
            features['var_div_len'] *= 0.4
            features['n_peaks'] *= 1.5
            
        else:
            # Default: shift towards anomalous distribution
            features['mean'] *= 0.38
            features['var'] *= 0.29
            features['std'] *= 0.42
            features['kurtosis'] *= 0.52
            features['n_peaks'] *= 1.77
            features['diff_peaks'] *= 0.45
            features['diff2_peaks'] *= 0.53
            features['diff_var'] *= 2.65
            features['diff2_var'] *= 26.5
        
        timestamp = datetime.now().isoformat()
        
        # Run through anomaly detection
        X_scaled = app_state['processor'].transform(
            pd.DataFrame([features], columns=app_state['processor'].feature_columns)
        )
        
        model = app_state['model']
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_scaled)
            probability = model.predict_proba(X_tensor).item()
            probability = sanitize_nan(probability) or 0.0  # Default to 0.0 if NaN
            prediction = int(probability >= get_anomaly_threshold())

        characteristics = extract_characteristics_from_features(features)
        
        anomaly_summary = {
            "probability": float(probability),
            "detected": bool(prediction),
            "timestamp": timestamp,
            "injected_type": anomaly_type,
            "injected_severity": severity,
            "characteristics": characteristics
        }
        
        # Step 2: Knowledge Graph Root Cause Analysis
        root_causes = []
        if prediction and channels:
            root_causes = app_state['kg'].find_root_causes(
                channels,
                anomaly_probability=float(probability),
                severity=severity.upper(),
                characteristics=characteristics,
                top_k=5
            )
        
        # Step 3: LLM+RAG Explanation
        explanation_result = {}
        if app_state['explainer'] and prediction:
            try:
                explanation_result = app_state['explainer'].generate_explanation(
                    anomaly_summary=anomaly_summary,
                    root_causes=root_causes,
                    affected_channels=channels
                )
            except Exception as e:
                logger.warning(f"LLM explanation failed: {e}")
                explanation_result = {}
        
        # Fallback explanation if LLM not available
        if prediction and not explanation_result:
            top_faults = [root_cause_fault_id(rc) for rc in root_causes[:3]]
            explanation_result = {
                "explanation": (
                    f"Test anomaly injected: {anomaly_type} with {severity} severity. "
                    + (f"Knowledge Graph identified probable causes: {', '.join(top_faults)}. " if top_faults else "")
                    + "The FCNN model successfully detected the anomaly pattern in the telemetry data."
                ),
                "severity": "HIGH" if probability >= 0.75 else "MEDIUM" if probability >= 0.5 else "LOW",
                "corrective_actions": [
                    "This is a test anomaly. In production, investigate the affected sensors.",
                    "Validate magnetometer calibration and check for magnetic interference.",
                    "Review ADCS control loop stability and reaction wheel health.",
                    "Increase telemetry sampling rate for detailed monitoring."
                ],
                "confidence": float(probability),
                "explanation_mode": "rule_based_fallback",
                "source_references": ["KG rules", "Test anomaly template"],
                "evidence_summary": build_evidence_summary(float(probability), channels, root_causes, characteristics)
            }
        elif not prediction:
            explanation_result = {
                "explanation": f"Test anomaly injection failed - the model did not detect the {anomaly_type} pattern. The severity ({severity}) may have been too low, or the model may not be sensitive to this anomaly type.",
                "severity": "LOW",
                "corrective_actions": [
                    "Try increasing the severity level to 'high'",
                    "Consider using a different anomaly type",
                    "Verify that the FCNN model is properly trained for this anomaly pattern"
                ],
                "confidence": float(1.0 - probability),
                "explanation_mode": "rule_based_fallback",
                "source_references": ["Test anomaly template"],
                "evidence_summary": build_evidence_summary(float(probability), channels, root_causes, characteristics)
            }
        
        # Build comprehensive response
        result = {
            "test_mode": True,
            "timestamp": timestamp,
            "injected_anomaly": {
                "type": anomaly_type,
                "severity": severity,
                "injected_features": {k: round(v, 4) for k, v in features.items()}
            },
            "anomaly_detection": anomaly_summary,
            "affected_channels": channels,
            "root_causes": [
                {
                    **rc,
                    "confidence": sanitize_nan(rc.get('confidence', 0.0)) or 0.0
                }
                for rc in serialize_root_causes(root_causes)
            ],
            "diagnosis": {
                "explanation": explanation_result.get('explanation', 'No explanation available'),
                "severity": explanation_result.get('severity', 'UNKNOWN'),
                "corrective_actions": explanation_result.get('corrective_actions', []),
                "confidence": sanitize_nan(explanation_result.get('confidence', 0.0)) or 0.0,
                "explanation_mode": explanation_result.get('explanation_mode', 'unknown'),
                "source_references": explanation_result.get('source_references', []),
                "evidence_summary": explanation_result.get(
                    'evidence_summary',
                    build_evidence_summary(float(probability), channels, root_causes, characteristics)
                )
            },
            "workflow_status": {
                "anomaly_detection": "✅ Completed" if prediction else "⚠️ No anomaly detected",
                "kg_root_cause_analysis": f"✅ Found {len(root_causes)} probable causes" if root_causes else "⚠️ No root causes identified",
                "llm_explanation": "✅ Generated" if explanation_result else "⚠️ LLM unavailable"
            }
        }
        
        logger.info(
            f"✅ Test anomaly completed: Type={anomaly_type}, "
            f"Detected={prediction}, Probability={probability:.2%}, "
            f"RootCauses={len(root_causes)}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Test anomaly injection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/inject-anomaly")
async def inject_anomaly_alias(request: Optional[Dict] = None):
    """Compatibility alias for legacy frontend route."""
    return await inject_test_anomaly(request)


@app.post("/api/v1/diagnosis/chat")
async def chat_diagnosis(request: Dict):
    """
    Interactive chat for fault diagnosis explanation
    
    Request body:
    {
        "message": "Why is the magnetometer showing this anomaly?",
        "context": {
            "detection": {...},
            "root_causes": [...],
            "channel": "CADC0872",
            "features": {...}
        },
        "session_id": "optional-session-id"
    }
    
    Returns AI-generated explanation and recommended actions
    """
    if app_state['explainer'] is None:
        context = request.get('context', {}) if isinstance(request, dict) else {}
        detection = context.get('detection', {})
        root_causes = context.get('root_causes', [])
        channel = context.get('channel', 'Unknown channel')
        user_message = request.get('message', '') if isinstance(request, dict) else ''

        probability = float(detection.get('probability', 0.0) or 0.0)
        severity = detection.get('severity', 'UNKNOWN')
        cause_lines = []
        for idx, rc in enumerate(root_causes[:3], 1):
            fault_name = rc.get('fault_name', rc.get('fault', 'Unknown'))
            confidence = float(rc.get('confidence', 0.0) or 0.0)
            cause_lines.append(f"{idx}. {fault_name} ({confidence*100:.1f}% confidence)")

        response_parts = [
            f"Deterministic diagnosis support is active for {channel}.",
            f"Current anomaly probability: {probability*100:.1f}% | Severity: {severity}."
        ]

        if cause_lines:
            response_parts.append("Top likely causes:\n" + "\n".join(cause_lines))

        if user_message:
            response_parts.append(f"Question received: {user_message}")

        response_parts.append(
            "Recommended immediate actions: validate sensor calibration, check ADCS control loop stability, and continue high-frequency monitoring."
        )

        return {
            "response": "\n\n".join(response_parts),
            "actions": [
                "Validate magnetometer and ADCS sensor calibration",
                "Inspect reaction wheel and actuator telemetry",
                "Increase telemetry polling and monitor trend evolution"
            ],
            "confidence": 0.65,
            "method": "rule_based_fallback",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        message = request.get('message', '')
        context = request.get('context', {})
        session_id = request.get('session_id', 'default')
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        logger.info(f"💬 Chat request: '{message[:50]}...'")

        chat_sessions = app_state.get('chat_sessions', {})
        history = chat_sessions.get(session_id, [])
        history.append({"role": "user", "content": message})
        # Keep only recent context to avoid unlimited growth
        history = history[-12:]
        chat_sessions[session_id] = history
        app_state['chat_sessions'] = chat_sessions
        context['chat_history'] = history

        if app_state['explainer'] is not None:
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(app_state['explainer'].chat_diagnosis, message, context),
                    timeout=CHAT_RESPONSE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"Chat response timed out after {CHAT_RESPONSE_TIMEOUT_SECONDS}s; using deterministic fallback"
                )
                detection = context.get('detection', {})
                root_causes = context.get('root_causes', [])
                channel = context.get('channel', 'Unknown')
                probability = float(detection.get('probability', 0.0) or 0.0)
                cause_lines = []
                for idx, rc in enumerate(root_causes[:3], 1):
                    fault_name = rc.get('fault_name', rc.get('fault', 'Unknown'))
                    confidence = float(rc.get('confidence', 0.0) or 0.0)
                    cause_lines.append(f"{idx}. {fault_name} ({confidence*100:.1f}% confidence)")

                response_parts = [
                    f"Live diagnosis is available for {channel}, but the LLM response exceeded the time budget.",
                    f"Current anomaly probability: {probability*100:.1f}% | Severity: {detection.get('severity', 'UNKNOWN')}.",
                ]

                if cause_lines:
                    response_parts.append("Top likely causes:\n" + "\n".join(cause_lines))

                response_parts.append(
                    "Immediate actions: validate sensor calibration, inspect ADCS control stability, and continue monitoring while the full explanation is being generated."
                )

                response = {
                    "response": "\n\n".join(response_parts),
                    "actions": [
                        "Validate magnetometer and ADCS sensor calibration",
                        "Inspect reaction wheel and actuator telemetry",
                        "Increase telemetry polling and monitor trend evolution",
                    ],
                    "confidence": 0.65,
                    "method": "timed_fallback",
                    "explanation_mode": "timed_fallback",
                    "source_references": ["ADCS fallback playbook"],
                    "evidence_summary": {
                        "affected_channels": [channel] if channel != 'Unknown' else [],
                        "probable_root_causes": [
                            {
                                "fault_id": rc.get('fault_name', rc.get('fault', 'Unknown')),
                                "confidence": float(rc.get('confidence', 0.0) or 0.0),
                            }
                            for rc in root_causes[:5]
                        ],
                        "anomaly_probability": probability,
                        "timestamp": context.get('timestamp'),
                    },
                }

            response['session_id'] = session_id
            response['timestamp'] = datetime.now().isoformat()
            history.append({"role": "assistant", "content": response.get('response', '')})
            app_state['chat_sessions'][session_id] = history[-12:]
            return response
        
        # Build RAG query with context
        detection = context.get('detection', {})
        root_causes = context.get('root_causes', [])
        channel = context.get('channel', 'Unknown')
        
        query = f"""
Current Diagnosis Context:
- Channel: {channel}
- Anomaly Probability: {detection.get('probability', 0)*100:.1f}%
- Severity: {detection.get('severity', 'Unknown')}
- Characteristics: {', '.join(detection.get('characteristics', []))}

Top Root Causes:
"""
        for i, rc in enumerate(root_causes[:3], 1):
            fault_name = rc.get('fault_name', rc.get('fault', 'Unknown'))
            confidence = rc.get('confidence', 0)
            query += f"\n{i}. {fault_name} ({confidence*100:.1f}%)"
        
        query += f"\n\nEngineer Question: {message}\n\nProvide expert guidance:"
        
        # Query RAG chain
        try:
            response = app_state['explainer'].qa_chain.invoke(query)
            
            # Extract actionable items from response
            actions = []
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if (line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')) or
                    'recommend' in line.lower() or
                    'should' in line.lower() or
                    'action' in line.lower()):
                    action = line.lstrip('1234567890.-•').strip()
                    if len(action) > 10:
                        actions.append(action)
            
            actions = actions[:5]  # Limit to 5 actions
            
            result = {
                "response": response,
                "actions": actions,
                "confidence": 0.85,
                "method": "rag",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Chat response generated ({len(response)} chars)")
            return result
            
        except Exception as e:
            logger.warning(f"RAG query failed: {e}")
            
            # Fallback response
            fallback = f"""
Deterministic diagnosis support is active for {channel}.

Anomaly probability: {detection.get('probability', 0)*100:.1f}%
Severity: {detection.get('severity', 'Unknown')}

Top probable root causes:
"""
            for i, rc in enumerate(root_causes[:3], 1):
                fault_name = rc.get('fault_name', rc.get('fault', 'Unknown'))
                confidence = rc.get('confidence', 0)
                description = rc.get('description', '')
                fallback += f"\n{i}. {fault_name} ({confidence*100:.1f}% confidence)"
                if description:
                    fallback += f"\n   → {description}"
            
            fallback += f"\n\nTo address your question: {message}\n\n"
            fallback += (
                "Recommended immediate actions: validate magnetometer calibration, "
                "inspect ADCS control loop stability, and continue high-frequency monitoring."
            )
            
            return {
                "response": fallback,
                "actions": [
                    "Validate magnetometer and ADCS sensor calibration",
                    "Inspect reaction wheel and actuator telemetry",
                    "Increase telemetry polling and monitor trend evolution"
                ],
                "confidence": 0.6,
                "method": "fallback",
                "timestamp": datetime.now().isoformat()
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat diagnosis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats")
async def get_statistics():
    """Get system statistics"""
    replay_engine = app_state.get('replay_engine')
    replay_channels = replay_engine.available_channels() if replay_engine is not None else []

    stats = {
        "model_info": {
            "architecture": "FCNN",
            "input_features": app_state['model'].input_dim if app_state['model'] else 0,
            "hidden_layers": app_state['model'].hidden_layers if app_state['model'] else [],
            "parameters": sum(p.numel() for p in app_state['model'].parameters()) if app_state['model'] else 0,
            "threshold": get_anomaly_threshold()
        },
        "knowledge_graph": {
            "nodes": app_state['kg'].graph.number_of_nodes() if app_state['kg'] else 0,
            "relationships": app_state['kg'].graph.number_of_edges() if app_state['kg'] else 0
        },
        "telemetry": {
            "replay_source": settings.SEGMENTS_CSV,
            "channel_count": len(replay_channels),
            "channels": replay_channels
        },
        "system": {
            "environment": settings.ENVIRONMENT,
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
    }
    
    return stats


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
