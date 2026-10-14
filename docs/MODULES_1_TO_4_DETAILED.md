# Modules 1 To 4 Detailed Flow

## Scope
This document tracks the full implementation path for the ESA CubeSat ADCS near real-time fault diagnosis system, from Module 1 to Module 4, with clear inputs, outputs, and runtime behavior.

## Module 1: Feature Extraction
Objective: Convert raw telemetry segments into stable statistical features for model inference.

Inputs:
- Segment telemetry windows from OPS-SAT ADCS channels.
- Channel focus for near real-time path: CADC0872, CADC0873, CADC0874.

Processing:
- Time and shape features: duration, len.
- Distribution features: mean, var, std, kurtosis, skew.
- Dynamics features: n_peaks, smooth peaks, diff peaks and variances.
- Normalized derived features for robust model compatibility.

Outputs:
- 18 feature values per segment (model input vector).

Key files:
- backend/src/processing/feature_extractor.py
- backend/src/processing/data_processor.py

## Module 2: Anomaly Detection (FCNN)
Objective: Detect anomalous ADCS behavior using the trained neural model.

Inputs:
- Feature vector from Module 1.

Processing:
- Processor scaling via trained data processor.
- FCNN inference to produce anomaly probability.
- Threshold decision for detected vs nominal.

Outputs:
- anomaly_detection: detected, probability, severity, timestamp.

Key files:
- backend/src/models/fcnn_model.py
- backend/src/models/fcnn_trainer.py
- backend/src/models/anomaly_detector.py
- models/trained/fcnn_anomaly_detector.pt

## Module 3: Root Cause Analysis (Knowledge Graph)
Objective: Map detected anomalies to likely ADCS root causes.

Inputs:
- Affected channels from detection pipeline.
- Severity/probability context.

Processing:
- Query ADCS ontology graph for candidate fault nodes.
- Rank causes with structure + severity + characteristic confidence.

Outputs:
- Ranked root causes with fault name, confidence, description, severity.

Key files:
- backend/src/knowledge_graph/kg_builder.py

## Module 4: Interactive Diagnosis (XAI + Chat)
Objective: Provide operational explanations and corrective actions.

Inputs:
- Anomaly summary + root causes from Modules 2 and 3.
- Operator question for chat.

Processing:
- RAG response when LLM service is available.
- Deterministic fallback response when LLM is unavailable.
- Action extraction for operations workflow.

Outputs:
- diagnosis: explanation, severity, corrective_actions, confidence.
- chat response with actionable guidance.

Key files:
- backend/src/explainability/diagnosis_explainer.py
- backend/src/api/main.py
- frontend/src/components/DiagnosisChatPanel.tsx

## Near Real-Time Runtime Path
1. Frontend requests next dataset-backed snapshot using /api/v1/telemetry/next.
2. Backend reads next row per magnetometer channel from dataset.csv.
3. Features are fed through processor + FCNN model.
4. If anomaly detected, KG root causes are computed.
5. Diagnosis payload is returned to frontend for dashboard panels and chat context.

## Single-Satellite Mission Model
- UI mission scope is now single satellite: ESA OPS-SAT CubeSat.
- Telemetry channels represent 3-axis ADCS magnetometer telemetry, not three satellites.

## Operational Notes
- LLM/Ollama is optional.
- If LLM is down, deterministic diagnosis and chat guidance remain active.
- For clean UI updates after code changes, clear frontend build cache and restart the frontend dev server.