"""
AdaBoost Baseline Model for Comparison
"""
from sklearn.ensemble import AdaBoostClassifier
from sklearn.tree import DecisionTreeClassifier
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, Tuple

from ..config import settings
from ..utils.logger import get_logger, LogContext

logger = get_logger()


class AdaBoostBaseline:
    """AdaBoost baseline model for anomaly detection"""
    
    def __init__(
        self,
        n_estimators: int = 100,
        learning_rate: float = 1.0,
        random_state: int = 42
    ):
        """
        Initialize AdaBoost model
        
        Args:
            n_estimators: Number of boosting iterations
            learning_rate: Learning rate
            random_state: Random seed
        """
        self.model = AdaBoostClassifier(
            base_estimator=DecisionTreeClassifier(max_depth=3),
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            random_state=random_state,
            algorithm='SAMME.R'
        )
        
        self.is_fitted = False
        logger.info(f"🌳 AdaBoost initialized with {n_estimators} estimators")
    
    def fit(self, X_train: np.ndarray, y_train: np.ndarray):
        """Train the model"""
        with LogContext("Training AdaBoost baseline"):
            self.model.fit(X_train, y_train)
            self.is_fitted = True
            logger.info("✅ AdaBoost training completed")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Get predictions"""
        return self.model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get probability predictions"""
        return self.model.predict_proba(X)[:, 1]
    
    def save(self, filepath: Path):
        """Save model to disk"""
        joblib.dump(self.model, filepath)
        logger.info(f"💾 AdaBoost model saved: {filepath}")
    
    @classmethod
    def load(cls, filepath: Path):
        """Load model from disk"""
        instance = cls()
        instance.model = joblib.load(filepath)
        instance.is_fitted = True
        logger.info(f"📂 AdaBoost model loaded: {filepath}")
        return instance
