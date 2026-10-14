# Evaluation Metrics Diagrams

This page summarizes the FCNN evaluation results from the latest experiment and provides Mermaid diagrams you can use in the project report or documentation.

## Experiment Snapshot

- Experiment: `fcnn_phase2_20260408_014653`
- Training samples: `1275`
- Validation samples: `319`
- Test samples: `529`
- Decision threshold: `0.77`
- Validation best F1 threshold: `0.57`

## 1. Evaluation Pipeline

```mermaid
flowchart LR
    A[Raw Telemetry Segments] --> B[Feature Extraction\n18 engineered features]
    B --> C[Imputation + Scaling\nTelemetryProcessor]
    C --> D[FCNN Inference\nSigmoid probability]
    D --> E{Threshold >= 0.77?}
    E -->|Yes| F[Anomaly]
    E -->|No| G[Normal]
    F --> H[KG Root Cause Analysis]
    H --> I[RAG + Ollama Explanation]
    G --> J[Nominal Monitoring]
```

## 2. Confusion Matrix Summary

Overall test-set confusion matrix:
- True Negative: `412`
- False Positive: `4`
- False Negative: `9`
- True Positive: `104`

```mermaid
pie title FCNN Confusion Matrix
    "True Negative (412)" : 412
    "True Positive (104)" : 104
    "False Negative (9)" : 9
    "False Positive (4)" : 4
```

## 3. Overall Metric Comparison

```mermaid
xychart-beta
    title "FCNN Overall Evaluation Metrics (%)"
    x-axis ["Accuracy", "Precision", "Recall", "F1", "ROC-AUC"]
    y-axis "Score" 0 --> 100
    bar [97.54, 96.30, 92.04, 94.12, 99.11]
```

## 4. Per-Channel F1 Score

```mermaid
xychart-beta
    title "Per-Channel F1 Score (%)"
    x-axis ["CADC0872", "CADC0873", "CADC0874", "CADC0884", "CADC0886", "CADC0888", "CADC0890", "CADC0892", "CADC0894"]
    y-axis "F1 Score" 0 --> 100
    bar [95.08, 92.06, 97.78, 0.00, 100.00, 95.65, 100.00, 92.31, 80.00]
```

## 5. Threshold Sensitivity

The evaluation found:
- Production threshold used in the model package: `0.77`
- Best threshold by validation F1: `0.57`
- Validation best F1: `0.9520`

```mermaid
flowchart TB
    A[Threshold Sweep] --> B[Precision]
    A --> C[Recall]
    A --> D[F1 Score]
    B --> E[Model Decision Threshold]
    C --> E
    D --> E
    E --> F[Selected Threshold = 0.77]
    D --> G[Best Validation Threshold = 0.57]
```

## 6. Interpretation Notes

- High accuracy and ROC-AUC show the FCNN separates normal and anomalous telemetry well.
- Recall is slightly lower than precision, so some anomalies are still missed.
- Per-channel results show the model is strongest on magnetometer channels and some photodiode channels.
- The best validation F1 threshold is lower than the production threshold, which means the production model is tuned to be more conservative.

## 7. Source Artifacts

The generated evaluation artifacts are stored in:
- `models/experiments/fcnn_phase2_20260408_014653/evaluation/roc_curve.png`
- `models/experiments/fcnn_phase2_20260408_014653/evaluation/precision_recall_curve.png`
- `models/experiments/fcnn_phase2_20260408_014653/evaluation/confusion_matrix.png`
- `models/experiments/fcnn_phase2_20260408_014653/evaluation/threshold_curve.png`
- `models/experiments/fcnn_phase2_20260408_014653/artifacts/training_history.png`
