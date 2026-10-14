"""
Model Evaluation and Metrics
Comprehensive evaluation suite for anomaly detection models
"""
import numpy as np
import torch
import json
from typing import Dict, Tuple, Optional, List
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    precision_recall_curve, roc_curve
)
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from ..utils.logger import get_logger, LogContext

logger = get_logger()


class ModelEvaluator:
    """Comprehensive model evaluation for anomaly detection"""
    
    @staticmethod
    def evaluate(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None,
        threshold: float = 0.5
    ) -> Dict[str, float]:
        """
        Compute comprehensive evaluation metrics
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_proba: Prediction probabilities (optional)
            threshold: Classification threshold
            
        Returns:
            Dictionary of metrics
        """
        with LogContext("Evaluating model performance"):
            metrics = {}
            
            # Basic metrics
            metrics['accuracy'] = accuracy_score(y_true, y_pred)
            metrics['precision'] = precision_score(y_true, y_pred, zero_division=0)
            metrics['recall'] = recall_score(y_true, y_pred, zero_division=0)
            metrics['f1_score'] = f1_score(y_true, y_pred, zero_division=0)
            
            # Confusion matrix
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
            metrics['true_negative'] = int(tn)
            metrics['false_positive'] = int(fp)
            metrics['false_negative'] = int(fn)
            metrics['true_positive'] = int(tp)
            
            # Derived metrics
            metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0
            metrics['false_positive_rate'] = fp / (fp + tn) if (fp + tn) > 0 else 0
            metrics['false_negative_rate'] = fn / (fn + tp) if (fn + tp) > 0 else 0
            
            # ROC AUC (if probabilities available)
            if y_proba is not None:
                try:
                    metrics['roc_auc'] = roc_auc_score(y_true, y_proba)
                except ValueError:
                    metrics['roc_auc'] = 0.0
            
            # Log metrics
            logger.info("📊 Evaluation Metrics:")
            logger.info(f"   Accuracy:  {metrics['accuracy']:.4f}")
            logger.info(f"   Precision: {metrics['precision']:.4f}")
            logger.info(f"   Recall:    {metrics['recall']:.4f}")
            logger.info(f"   F1 Score:  {metrics['f1_score']:.4f}")
            if y_proba is not None:
                logger.info(f"   ROC AUC:   {metrics['roc_auc']:.4f}")
            
            return metrics
    
    @staticmethod
    def print_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray):
        """Print formatted confusion matrix"""
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        
        print("\n╔══════════════════════════════════════╗")
        print("║        Confusion Matrix              ║")
        print("╠══════════════════════════════════════╣")
        print(f"║  TN: {cm[0,0]:6d}  |  FP: {cm[0,1]:6d}     ║")
        print(f"║  FN: {cm[1,0]:6d}  |  TP: {cm[1,1]:6d}     ║")
        print("╚══════════════════════════════════════╝\n")
    
    @staticmethod
    def plot_confusion_matrix(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        save_path: Optional[Path] = None
    ):
        """Plot confusion matrix heatmap"""
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(
            cm,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=['Normal', 'Anomaly'],
            yticklabels=['Normal', 'Anomaly']
        )
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.title('Confusion Matrix')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"💾 Confusion matrix saved: {save_path}")
        
        plt.close()
    
    @staticmethod
    def plot_roc_curve(
        y_true: np.ndarray,
        y_proba: np.ndarray,
        save_path: Optional[Path] = None
    ):
        """Plot ROC curve"""
        if len(np.unique(y_true)) < 2:
            plt.figure(figsize=(8, 6))
            plt.text(0.5, 0.5, 'ROC unavailable for single-class slice', ha='center', va='center')
            plt.axis('off')
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"💾 ROC curve saved: {save_path}")
            plt.close()
            return

        fpr, tpr, _ = roc_curve(y_true, y_proba)
        auc = roc_auc_score(y_true, y_proba)
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, label=f'ROC Curve (AUC = {auc:.4f})', linewidth=2)
        plt.plot([0, 1], [0, 1], 'k--', label='Random Classifier')
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"💾 ROC curve saved: {save_path}")
        
        plt.close()
    
    @staticmethod
    def plot_precision_recall_curve(
        y_true: np.ndarray,
        y_proba: np.ndarray,
        save_path: Optional[Path] = None
    ):
        """Plot Precision-Recall curve"""
        if len(np.unique(y_true)) < 2:
            plt.figure(figsize=(8, 6))
            plt.text(0.5, 0.5, 'PR curve unavailable for single-class slice', ha='center', va='center')
            plt.axis('off')
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"💾 Precision-Recall curve saved: {save_path}")
            plt.close()
            return

        precision, recall, _ = precision_recall_curve(y_true, y_proba)
        
        plt.figure(figsize=(8, 6))
        plt.plot(recall, precision, linewidth=2)
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title('Precision-Recall Curve')
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"💾 Precision-Recall curve saved: {save_path}")
        
        plt.close()

    @staticmethod
    def plot_threshold_curve(
        y_true: np.ndarray,
        y_proba: np.ndarray,
        save_path: Optional[Path] = None
    ):
        """Plot threshold sweep for precision/recall/F1 trade-off."""
        thresholds = np.linspace(0.0, 1.0, 101)
        precisions = []
        recalls = []
        f1_scores = []

        for threshold in thresholds:
            y_pred = (y_proba >= threshold).astype(int)
            precisions.append(precision_score(y_true, y_pred, zero_division=0))
            recalls.append(recall_score(y_true, y_pred, zero_division=0))
            f1_scores.append(f1_score(y_true, y_pred, zero_division=0))

        plt.figure(figsize=(10, 6))
        plt.plot(thresholds, precisions, label='Precision', linewidth=2)
        plt.plot(thresholds, recalls, label='Recall', linewidth=2)
        plt.plot(thresholds, f1_scores, label='F1 Score', linewidth=2)
        plt.xlabel('Decision Threshold')
        plt.ylabel('Score')
        plt.title('Threshold Sensitivity Analysis')
        plt.legend()
        plt.grid(True, alpha=0.3)

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"💾 Threshold curve saved: {save_path}")

        plt.close()

    @staticmethod
    def find_best_threshold(
        y_true: np.ndarray,
        y_proba: np.ndarray,
        metric: str = 'f1'
    ) -> Dict[str, float]:
        """Find the best decision threshold for a target metric."""
        thresholds = np.linspace(0.0, 1.0, 101)
        best = {'threshold': 0.5, 'score': -1.0}

        for threshold in thresholds:
            y_pred = (y_proba >= threshold).astype(int)
            if metric == 'f1':
                score = f1_score(y_true, y_pred, zero_division=0)
            elif metric == 'precision':
                score = precision_score(y_true, y_pred, zero_division=0)
            elif metric == 'recall':
                score = recall_score(y_true, y_pred, zero_division=0)
            else:
                score = f1_score(y_true, y_pred, zero_division=0)

            if score > best['score']:
                best = {'threshold': float(threshold), 'score': float(score)}

        return best

    @staticmethod
    def evaluate_by_channel(
        channels: List[str],
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None
    ) -> Dict[str, Dict]:
        """Compute per-channel metrics for evaluation reporting."""
        summary: Dict[str, Dict] = {}

        channels_arr = np.asarray(channels)
        unique_channels = sorted(pd.unique(channels_arr)) if len(channels_arr) else []

        for channel in unique_channels:
            mask = channels_arr == channel
            if mask.sum() == 0:
                continue

            channel_true = y_true[mask]
            channel_pred = y_pred[mask]
            channel_metrics = ModelEvaluator.evaluate(channel_true, channel_pred, None)

            if y_proba is not None:
                channel_metrics['roc_auc'] = float(roc_auc_score(channel_true, y_proba[mask])) if len(np.unique(channel_true)) > 1 else 0.0

            summary[str(channel)] = channel_metrics

        return summary

    @staticmethod
    def save_metrics_json(metrics: Dict, save_path: Path):
        """Persist metrics as JSON for experiment tracking."""
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as handle:
            json.dump(metrics, handle, indent=2, default=str)
        logger.info(f"💾 Metrics saved: {save_path}")
    
    @staticmethod
    def plot_training_history(
        history: Dict,
        save_path: Optional[Path] = None
    ):
        """Plot training history"""
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        
        # Loss plot
        axes[0].plot(history['train_loss'], label='Train Loss', linewidth=2)
        if 'val_loss' in history and history['val_loss']:
            axes[0].plot(history['val_loss'], label='Val Loss', linewidth=2)
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Loss')
        axes[0].set_title('Training & Validation Loss')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Accuracy plot
        axes[1].plot(history['train_acc'], label='Train Accuracy', linewidth=2)
        if 'val_acc' in history and history['val_acc']:
            axes[1].plot(history['val_acc'], label='Val Accuracy', linewidth=2)
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Accuracy')
        axes[1].set_title('Training & Validation Accuracy')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"💾 Training history saved: {save_path}")
        
        plt.close()
    
    @staticmethod
    def generate_evaluation_report(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None,
        output_dir: Optional[Path] = None,
        channels: Optional[List[str]] = None,
        threshold: float = 0.5
    ) -> Dict:
        """
        Generate complete evaluation report with all metrics and plots
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_proba: Prediction probabilities
            output_dir: Directory to save plots
            
        Returns:
            Dictionary of metrics
        """
        with LogContext("Generating evaluation report"):
            # Compute metrics
            metrics = ModelEvaluator.evaluate(y_true, y_pred, y_proba)
            metrics['threshold'] = float(threshold)

            if y_proba is not None:
                metrics['best_threshold'] = ModelEvaluator.find_best_threshold(y_true, y_proba, metric='f1')
            
            # Print confusion matrix
            ModelEvaluator.print_confusion_matrix(y_true, y_pred)
            
            # Generate plots if output directory specified
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Confusion matrix plot
                ModelEvaluator.plot_confusion_matrix(
                    y_true, y_pred,
                    save_path=output_dir / 'confusion_matrix.png'
                )
                
                if y_proba is not None:
                    # ROC curve
                    ModelEvaluator.plot_roc_curve(
                        y_true, y_proba,
                        save_path=output_dir / 'roc_curve.png'
                    )
                    
                    # Precision-Recall curve
                    ModelEvaluator.plot_precision_recall_curve(
                        y_true, y_proba,
                        save_path=output_dir / 'precision_recall_curve.png'
                    )

                    # Threshold analysis
                    ModelEvaluator.plot_threshold_curve(
                        y_true, y_proba,
                        save_path=output_dir / 'threshold_curve.png'
                    )

                if channels is not None:
                    metrics['per_channel'] = ModelEvaluator.evaluate_by_channel(
                        channels=channels,
                        y_true=y_true,
                        y_pred=y_pred,
                        y_proba=y_proba
                    )

                ModelEvaluator.save_metrics_json(metrics, output_dir / 'metrics.json')
            
            logger.info("✅ Evaluation report generated")
            return metrics
