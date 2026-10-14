"""Phase 2 reproducible FCNN training and evaluation pipeline.

This script rebuilds anomaly detection as a proper experiment:
- deterministic seeding
- train/validation/test separation
- threshold selection from validation set
- per-channel metrics
- artifact export (plots + JSON manifest)
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch

sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings, setup_directories  # noqa: E402
from src.ingestion import TelemetryIngestor  # noqa: E402
from src.models import FCNN, FCNNTrainer  # noqa: E402
from src.models.model_evaluator import ModelEvaluator  # noqa: E402
from src.processing import TelemetryProcessor  # noqa: E402
from src.utils.logger import LoggerSetup, LogContext, get_logger  # noqa: E402


@dataclass
class ExperimentManifest:
    experiment_name: str
    created_at: str
    seed: int
    train_samples: int
    val_samples: int
    test_samples: int
    feature_columns: List[str]
    threshold: float
    validation_best_f1: float
    metrics: Dict
    training_config: Dict


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def split_train_val(df: pd.DataFrame, validation_ratio: float = 0.2, seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministically split a train dataframe into train and validation subsets."""
    if df.empty:
        raise ValueError("Training dataframe is empty")

    shuffled = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    split_index = max(1, int(len(shuffled) * (1 - validation_ratio)))
    train_df = shuffled.iloc[:split_index].copy()
    val_df = shuffled.iloc[split_index:].copy()

    if val_df.empty:
        val_df = train_df.tail(max(1, len(train_df) // 5)).copy()
        train_df = train_df.iloc[:-len(val_df)].copy()

    return train_df, val_df


def build_experiment_dir() -> Tuple[str, Path]:
    experiment_name = f"fcnn_phase2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    experiment_dir = settings.MODELS_DIR / "experiments" / experiment_name
    (experiment_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (experiment_dir / "evaluation").mkdir(parents=True, exist_ok=True)
    (experiment_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    return experiment_name, experiment_dir


def main() -> None:
    setup_directories()
    LoggerSetup.setup(settings.LOGS_DIR, level=settings.LOG_LEVEL)
    logger = get_logger()

    seed = 42
    set_seed(seed)

    logger.info("=" * 80)
    logger.info("PHASE 2: REPRODUCIBLE FCNN TRAINING + EVALUATION")
    logger.info("=" * 80)

    experiment_name, experiment_dir = build_experiment_dir()
    logger.info(f"Experiment: {experiment_name}")
    logger.info(f"Output directory: {experiment_dir}")
    logger.info(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")

    with LogContext("Load and validate dataset"):
        ingestor = TelemetryIngestor()
        dataset_df = ingestor.load_dataset()
        ingestor.validate_data(dataset_df)

        if 'train' not in dataset_df.columns:
            raise ValueError("dataset.csv must contain a 'train' column for reproducible splitting")

        train_df = dataset_df[dataset_df['train'] == 1].copy()
        test_df = dataset_df[dataset_df['train'] == 0].copy()
        train_split_df, val_df = split_train_val(train_df, validation_ratio=0.2, seed=seed)
        feature_cols = ingestor.get_feature_columns(dataset_df)

        logger.info(f"Train samples: {len(train_split_df)}")
        logger.info(f"Validation samples: {len(val_df)}")
        logger.info(f"Test samples: {len(test_df)}")
        logger.info(f"Feature columns: {len(feature_cols)}")

    with LogContext("Prepare scaled feature matrices"):
        processor = TelemetryProcessor(scaler_type='standard')
        X_train_scaled, X_test_scaled, y_train, y_test = processor.prepare_training_data(
            train_df=train_split_df,
            test_df=test_df,
            feature_cols=feature_cols,
            target_col='anomaly'
        )

        # Rebuild a validation matrix using the already fitted processor.
        val_features = val_df[feature_cols].copy()
        val_features = processor.handle_missing_values(val_features, feature_cols, fit=False)
        X_val_scaled = processor.transform(val_features)
        y_val = val_df['anomaly'].values.astype(np.float32)

        processor_path = experiment_dir / 'artifacts' / 'data_processor.pkl'
        processor.save(processor_path)
        logger.info(f"Saved processor: {processor_path}")

        runtime_processor_path = settings.MODELS_DIR / 'trained' / 'data_processor.pkl'
        processor.save(runtime_processor_path)
        logger.info(f"Saved runtime processor: {runtime_processor_path}")

    with LogContext("Initialize model and trainer"):
        model = FCNN(
            input_dim=len(feature_cols),
            hidden_layers=settings.FCNN_HIDDEN_LAYERS,
            dropout_rate=settings.FCNN_DROPOUT_RATE,
            use_batch_norm=True,
            output_dim=1,
        )
        trainer = FCNNTrainer(model=model, learning_rate=settings.FCNN_LEARNING_RATE)
        logger.info(model.get_model_summary())

    with LogContext("Train FCNN"):
        history = trainer.fit(
            X_train=X_train_scaled,
            y_train=y_train,
            X_val=X_val_scaled,
            y_val=y_val,
            epochs=settings.FCNN_EPOCHS,
            batch_size=settings.FCNN_BATCH_SIZE,
            early_stopping_patience=settings.FCNN_EARLY_STOPPING_PATIENCE,
            checkpoint_dir=experiment_dir / 'checkpoints'
        )

        ModelEvaluator.plot_training_history(history, save_path=experiment_dir / 'artifacts' / 'training_history.png')

    with LogContext("Validate threshold and test model"):
        trainer.model.eval()
        with torch.no_grad():
            val_tensor = torch.FloatTensor(X_val_scaled).to(trainer.device)
            test_tensor = torch.FloatTensor(X_test_scaled).to(trainer.device)
            val_proba = trainer.model.predict_proba(val_tensor).cpu().numpy().flatten()
            test_proba = trainer.model.predict_proba(test_tensor).cpu().numpy().flatten()

        best_threshold = ModelEvaluator.find_best_threshold(y_val, val_proba, metric='f1')
        threshold = best_threshold['threshold']

        y_test_pred = (test_proba >= threshold).astype(int)
        metrics = ModelEvaluator.generate_evaluation_report(
            y_true=y_test,
            y_pred=y_test_pred,
            y_proba=test_proba,
            output_dir=experiment_dir / 'evaluation',
            channels=test_df['channel'].astype(str).tolist(),
            threshold=threshold,
        )

        val_pred = (val_proba >= threshold).astype(int)
        val_metrics = ModelEvaluator.evaluate(y_val, val_pred, val_proba)

        logger.info("=" * 80)
        logger.info("VALIDATION + TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Validation F1 @ threshold {threshold:.2f}: {val_metrics['f1_score']:.4f}")
        logger.info(f"Test Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"Test Precision: {metrics['precision']:.4f}")
        logger.info(f"Test Recall:    {metrics['recall']:.4f}")
        logger.info(f"Test F1 Score:  {metrics['f1_score']:.4f}")
        logger.info(f"Test ROC AUC:   {metrics.get('roc_auc', 0.0):.4f}")

    with LogContext("Save model and manifest"):
        model_path = settings.MODELS_DIR / 'trained' / 'fcnn_anomaly_detector.pt'
        model_path.parent.mkdir(parents=True, exist_ok=True)

        trainer.save_model(
            filepath=model_path,
            metadata={
                'experiment_name': experiment_name,
                'seed': seed,
                'feature_columns': feature_cols,
                'threshold': threshold,
                'validation_metrics': val_metrics,
                'test_metrics': metrics,
                'training_history_length': len(history.get('train_loss', [])),
                'training_config': {
                    'hidden_layers': settings.FCNN_HIDDEN_LAYERS,
                    'dropout_rate': settings.FCNN_DROPOUT_RATE,
                    'learning_rate': settings.FCNN_LEARNING_RATE,
                    'batch_size': settings.FCNN_BATCH_SIZE,
                    'epochs': settings.FCNN_EPOCHS,
                    'early_stopping_patience': settings.FCNN_EARLY_STOPPING_PATIENCE,
                },
            }
        )

        manifest = ExperimentManifest(
            experiment_name=experiment_name,
            created_at=datetime.now().isoformat(),
            seed=seed,
            train_samples=len(train_split_df),
            val_samples=len(val_df),
            test_samples=len(test_df),
            feature_columns=feature_cols,
            threshold=threshold,
            validation_best_f1=best_threshold['score'],
            metrics=metrics,
            training_config={
                'hidden_layers': settings.FCNN_HIDDEN_LAYERS,
                'dropout_rate': settings.FCNN_DROPOUT_RATE,
                'learning_rate': settings.FCNN_LEARNING_RATE,
                'batch_size': settings.FCNN_BATCH_SIZE,
                'epochs': settings.FCNN_EPOCHS,
                'early_stopping_patience': settings.FCNN_EARLY_STOPPING_PATIENCE,
            }
        )

        manifest_path = experiment_dir / 'manifest.json'
        with open(manifest_path, 'w', encoding='utf-8') as handle:
            json.dump(asdict(manifest), handle, indent=2, default=str)

        logger.info(f"Saved model: {model_path}")
        logger.info(f"Saved manifest: {manifest_path}")
        logger.info(f"Saved experiment artifacts: {experiment_dir}")

    logger.info("=" * 80)
    logger.info("PHASE 2 COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        logger = get_logger()
        logger.exception(f"Phase 2 training failed: {exc}")
        raise