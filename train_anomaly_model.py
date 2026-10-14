"""Quick training script for anomaly detector"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from backend.src.models.anomaly_detector import train_anomaly_detector

if __name__ == '__main__':
    trainer, metrics = train_anomaly_detector()
    
    print(f"\n📊 Final Metrics:")
    print(f"  Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1 Score:  {metrics['f1_score']:.4f}")
    print(f"  AUC:       {metrics['auc']:.4f}")
