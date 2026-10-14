"""
Complete End-to-End Training Script for FCNN Anomaly Detection Model
Production-ready training pipeline with comprehensive logging and checkpointing
"""
import sys
from pathlib import Path
import torch
import numpy as np
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings, setup_directories
from src.utils.logger import LoggerSetup, get_logger, LogContext
from src.ingestion import TelemetryIngestor
from src.processing import TelemetryProcessor
from src.models import FCNN, FCNNTrainer
from src.models.model_evaluator import ModelEvaluator


def main():
    """Main training pipeline"""
    
    # Setup directories and logging
    setup_directories()
    LoggerSetup.setup(settings.LOGS_DIR, level=settings.LOG_LEVEL)
    logger = get_logger()
    
    logger.info("="*70)
    logger.info("🛰️  SATELLITE TELEMETRY ANOMALY DETECTION - FCNN TRAINING")
    logger.info("="*70)
    
    # Training configuration
    EXPERIMENT_NAME = f"fcnn_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    EXPERIMENT_DIR = settings.MODELS_DIR / "experiments" / EXPERIMENT_NAME
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📁 Experiment: {EXPERIMENT_NAME}")
    logger.info(f"📂 Output directory: {EXPERIMENT_DIR}")
    logger.info(f"🖥️  Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    
    # ========================================================================
    # STEP 1: DATA INGESTION
    # ========================================================================
    with LogContext("Step 1: Data Ingestion"):
        ingestor = TelemetryIngestor()
        
        # Load dataset with pre-computed features
        logger.info("📡 Loading ESA OPS-SAT ADCS telemetry dataset...")
        dataset_df = ingestor.load_dataset()
        
        # Validate data
        validation_report = ingestor.validate_data(dataset_df)
        
        # Split train/test
        train_df, test_df = ingestor.get_train_test_split(dataset_df)
        
        # Get feature columns
        feature_cols = ingestor.get_feature_columns(dataset_df)
        logger.info(f"✅ Features: {len(feature_cols)} columns")
    
    # ========================================================================
    # STEP 2: DATA PROCESSING
    # ========================================================================
    with LogContext("Step 2: Data Processing & Feature Scaling"):
        processor = TelemetryProcessor(scaler_type='standard')
        
        # Prepare training data
        X_train, X_test, y_train, y_test = processor.prepare_training_data(
            train_df=train_df,
            test_df=test_df,
            feature_cols=feature_cols,
            target_col='anomaly'
        )
        
        # Save processor for inference
        processor_path = EXPERIMENT_DIR / "data_processor.pkl"
        processor.save(processor_path)
        logger.info(f"💾 Data processor saved: {processor_path}")
    
    # ========================================================================
    # STEP 3: MODEL INITIALIZATION
    # ========================================================================
    with LogContext("Step 3: Model Initialization"):
        input_dim = X_train.shape[1]
        
        model = FCNN(
            input_dim=input_dim,
            hidden_layers=settings.FCNN_HIDDEN_LAYERS,
            dropout_rate=settings.FCNN_DROPOUT_RATE,
            use_batch_norm=True,
            output_dim=1
        )
        
        logger.info(model.get_model_summary())
    
    # ========================================================================
    # STEP 4: MODEL TRAINING
    # ========================================================================
    with LogContext("Step 4: Model Training"):
        trainer = FCNNTrainer(
            model=model,
            learning_rate=settings.FCNN_LEARNING_RATE
        )
        
        # Train with validation split
        train_ratio = 0.8
        split_idx = int(len(X_train) * train_ratio)
        
        X_train_split = X_train[:split_idx]
        y_train_split = y_train[:split_idx]
        X_val_split = X_train[split_idx:]
        y_val_split = y_train[split_idx:]
        
        logger.info(f"📊 Training split: {len(X_train_split)} samples")
        logger.info(f"📊 Validation split: {len(X_val_split)} samples")
        
        # Train model
        history = trainer.fit(
            X_train=X_train_split,
            y_train=y_train_split,
            X_val=X_val_split,
            y_val=y_val_split,
            epochs=settings.FCNN_EPOCHS,
            batch_size=settings.FCNN_BATCH_SIZE,
            early_stopping_patience=settings.FCNN_EARLY_STOPPING_PATIENCE,
            checkpoint_dir=EXPERIMENT_DIR / "checkpoints"
        )
        
        # Plot training history
        ModelEvaluator.plot_training_history(
            history,
            save_path=EXPERIMENT_DIR / "training_history.png"
        )
    
    # ========================================================================
    # STEP 5: MODEL EVALUATION
    # ========================================================================
    with LogContext("Step 5: Model Evaluation"):
        # Evaluation on test set
        model.eval()
        
        with torch.no_grad():
            X_test_tensor = torch.FloatTensor(X_test).to(trainer.device)
            y_test_proba = model.predict_proba(X_test_tensor).cpu().numpy().flatten()
            y_test_pred = (y_test_proba >= 0.5).astype(int)
        
        # Generate comprehensive evaluation report
        metrics = ModelEvaluator.generate_evaluation_report(
            y_true=y_test,
            y_pred=y_test_pred,
            y_proba=y_test_proba,
            output_dir=EXPERIMENT_DIR / "evaluation"
        )
        
        # Print final results
        logger.info("="*70)
        logger.info("🎯 FINAL TEST SET RESULTS")
        logger.info("="*70)
        logger.info(f"   Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"   Precision: {metrics['precision']:.4f}")
        logger.info(f"   Recall:    {metrics['recall']:.4f}")
        logger.info(f"   F1 Score:  {metrics['f1_score']:.4f}")
        logger.info(f"   ROC AUC:   {metrics['roc_auc']:.4f}")
        logger.info("="*70)
        
        # Check if target accuracy achieved
        if metrics['accuracy'] >= 0.90:
            logger.info("✅ Target accuracy (>90%) ACHIEVED!")
        else:
            logger.warning(f"⚠️  Target accuracy not met. Current: {metrics['accuracy']:.2%}")
    
    # ========================================================================
    # STEP 6: MODEL SAVING
    # ========================================================================
    with LogContext("Step 6: Saving Production Model"):
        # Save final model
        model_path = settings.MODELS_DIR / "trained" / "fcnn_anomaly_detector.pt"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        trainer.save_model(
            filepath=model_path,
            metadata={
                'experiment_name': EXPERIMENT_NAME,
                'train_samples': len(X_train),
                'test_samples': len(X_test),
                'features': feature_cols,
                'test_metrics': metrics,
                'training_config': {
                    'hidden_layers': settings.FCNN_HIDDEN_LAYERS,
                    'dropout_rate': settings.FCNN_DROPOUT_RATE,
                    'learning_rate': settings.FCNN_LEARNING_RATE,
                    'batch_size': settings.FCNN_BATCH_SIZE,
                    'epochs_trained': len(history['train_loss'])
                }
            }
        )
        
        logger.info(f"💾 Production model saved: {model_path}")
        logger.info(f"📊 Experiment artifacts saved: {EXPERIMENT_DIR}")
    
    logger.info("="*70)
    logger.info("✅ TRAINING PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("="*70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger = get_logger()
        logger.exception(f"❌ Training failed with error: {e}")
        sys.exit(1)
