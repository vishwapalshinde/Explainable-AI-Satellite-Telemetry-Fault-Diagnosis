"""
Module 2: Anomaly Detection - FCNN Training and Inference

Train FCNN model on dataset.csv features and provide real-time anomaly detection.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, Tuple, Optional
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, classification_report, roc_auc_score, roc_curve

from ..config import settings
from ..utils.logger import get_logger, LogContext
from ..processing.feature_extractor import FEATURE_COLUMNS

logger = get_logger()


class CharacteristicsExtractor:
    """Extract anomaly characteristics from features for RCA"""
    
    @staticmethod
    def extract_characteristics(features: Dict[str, float]) -> list:
        """
        Determine observable characteristics from extracted features.
        Used to map technical anomalies to KG reasoning.
        """
        characteristics = []
        
        # High variance indicates signal instability
        if features.get('var', 0) > 5e-11:
            characteristics.append('high_variance')
        
        # Large mean shift indicates bias
        if abs(features.get('mean', 0)) > 5e-7:
            characteristics.append('mean_shift')
        
        # Peaks indicate oscillations/resonance
        if features.get('n_peaks', 0) > 5:
            characteristics.append('oscillation')
        
        # High kurtosis indicates outliers
        kurt = features.get('kurtosis', 0)
        if kurt < -0.5 or kurt > 1.5:
            characteristics.append('outliers')
        
        # Derivative variance indicates unexpected dynamics
        if features.get('diff_var', 0) > 1e-4:
            characteristics.append('dynamics_change')
        
        return characteristics


class FCNN(nn.Module):
    """
    Fully Connected Neural Network for Anomaly Detection
    
    Architecture: 17 input features → 128 → 64 → 32 → 1 output
    Used for binary classification (normal vs anomaly)
    """
    
    def __init__(
        self,
        input_dim: int = 17,
        hidden_dims: list = None,
        dropout_rate: float = 0.3,
        use_batch_norm: bool = True
    ):
        """
        Initialize FCNN architecture
        
        Args:
            input_dim: Number of input features (17 for ADCS)
            hidden_dims: List of hidden layer dimensions
            dropout_rate: Dropout probability
            use_batch_norm: Whether to use batch normalization
        """
        super(FCNN, self).__init__()
        
        if hidden_dims is None:
            hidden_dims = [128, 64, 32]
        
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims
        self.dropout_rate = dropout_rate
        self.use_batch_norm = use_batch_norm
        
        # Build network
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            # Linear layer
            layers.append(nn.Linear(prev_dim, hidden_dim))
            
            # Batch normalization
            if use_batch_norm:
                layers.append(nn.BatchNorm1d(hidden_dim))
            
            # Activation
            layers.append(nn.ReLU())
            
            # Dropout
            layers.append(nn.Dropout(dropout_rate))
            
            prev_dim = hidden_dim
        
        # Output layer
        layers.append(nn.Linear(prev_dim, 1))
        layers.append(nn.Sigmoid())  # Binary classification output
        
        self.network = nn.Sequential(*layers)
        
        logger.debug(f"✅ FCNN initialized: {input_dim} → {' → '.join(map(str, hidden_dims))} → 1")
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through network"""
        return self.network(x)
    
    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """
        Predict anomaly probability
        
        Args:
            x: Input tensor of features
            
        Returns:
            Tensor of anomaly probabilities (0.0-1.0)
        """
        with torch.no_grad():
            probas = self.forward(x)
        return probas


class AnomalyDetectionTrainer:
    """
    Train FCNN for anomaly detection on dataset.csv
    Handles model training, validation, and checkpoint saving
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize trainer"""
        self.data_dir = data_dir or settings.DATA_DIR
        self.dataset_path = self.data_dir / settings.DATASET_CSV
        
        self.model = None
        self.scaler = StandardScaler()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.training_history = {}
        
        logger.info(f"🎯 Anomaly Detection Trainer initialized on device: {self.device}")
    
    def prepare_data(self, test_size: float = 0.2) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Load and prepare dataset.csv for training
        
        Args:
            test_size: Proportion of data for testing
            
        Returns:
            Tuple of (X_train, y_train, X_test, y_test) tensors
        """
        with LogContext("Preparing training data"):
            df = pd.read_csv(self.dataset_path)
            
            logger.info(f"📊 Loaded {len(df)} segments from dataset.csv")
            
            # Extract features and labels
            X = df[FEATURE_COLUMNS].values.astype(np.float32)
            y = df['anomaly'].values.astype(np.float32)
            
            # Use 'train' column for split if available, otherwise random split
            if 'train' in df.columns:
                train_mask = df['train'] == 1
                X_train, y_train = X[train_mask], y[train_mask]
                X_test, y_test = X[~train_mask], y[~train_mask]
                logger.info(f"📊 Using 'train' column split")
            else:
                # Use simple random split
                np.random.seed(42)
                split_idx = int(len(X) * (1 - test_size))
                indices = np.random.permutation(len(X))
                train_idx, test_idx = indices[:split_idx], indices[split_idx:]
                
                X_train, y_train = X[train_idx], y[train_idx]
                X_test, y_test = X[test_idx], y[test_idx]
            
            # Normalize features
            X_train = self.scaler.fit_transform(X_train)
            X_test = self.scaler.transform(X_test)
            
            # Convert to tensors
            X_train_tr = torch.FloatTensor(X_train).to(self.device)
            y_train_tr = torch.FloatTensor(y_train).reshape(-1, 1).to(self.device)
            X_test_tr = torch.FloatTensor(X_test).to(self.device)
            y_test_tr = torch.FloatTensor(y_test).reshape(-1, 1).to(self.device)
            
            # Log class distribution
            train_anomaly = y_train.sum()
            test_anomaly = y_test.sum()
            logger.info(f"📊 Train: {len(y_train)} samples ({train_anomaly:.0f} anomalies, {100*train_anomaly/len(y_train):.1f}%)")
            logger.info(f"📊 Test:  {len(y_test)} samples ({test_anomaly:.0f} anomalies, {100*test_anomaly/len(y_test):.1f}%)")
            
            return X_train_tr, y_train_tr, X_test_tr, y_test_tr
    
    def train(
        self,
        X_train: torch.Tensor,
        y_train: torch.Tensor,
        X_test: Optional[torch.Tensor] = None,
        y_test: Optional[torch.Tensor] = None,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        weight_decay: float = 1e-4
    ) -> Dict:
        """
        Train FCNN model
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_test: Optional test features for validation
            y_test: Optional test labels
            epochs: Number of epochs
            batch_size: Batch size
            learning_rate: Learning rate
            weight_decay: L2 regularization
            
        Returns:
            Training history dict
        """
        with LogContext("Training FCNN model"):
            # Initialize model
            self.model = FCNN(input_dim=X_train.shape[1]).to(self.device)
            
            # Loss and optimizer
            criterion = nn.BCELoss()
            optimizer = optim.Adam(self.model.parameters(), lr=learning_rate, weight_decay=weight_decay)
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5, verbose=False)
            
            # Data loader
            train_dataset = TensorDataset(X_train, y_train)
            train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
            
            # Training loop
            history = {
                'train_loss': [],
                'test_loss': [],
                'test_accuracy': [],
                'test_auc': []
            }
            
            best_test_loss = float('inf')
            patience_counter = 0
            
            for epoch in range(epochs):
                # Training phase
                self.model.train()
                train_loss = 0.0
                
                for batch_X, batch_y in train_loader:
                    optimizer.zero_grad()
                    outputs = self.model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()
                
                train_loss /= len(train_loader)
                history['train_loss'].append(train_loss)
                
                # Validation phase
                if X_test is not None and y_test is not None:
                    self.model.eval()
                    with torch.no_grad():
                        test_outputs = self.model(X_test)
                        test_loss = criterion(test_outputs, y_test).item()
                        
                        # Calculate metrics
                        predictions = (test_outputs.cpu() >= 0.5).numpy().flatten()
                        test_acc = (predictions == y_test.cpu().numpy().flatten()).mean()
                        
                        try:
                            test_auc = roc_auc_score(y_test.cpu().numpy(), test_outputs.cpu().numpy())
                        except:
                            test_auc = 0.0
                        
                        history['test_loss'].append(test_loss)
                        history['test_accuracy'].append(test_acc)
                        history['test_auc'].append(test_auc)
                    
                    # Learning rate scheduling
                    scheduler.step(test_loss)
                    
                    # Early stopping
                    if test_loss < best_test_loss:
                        best_test_loss = test_loss
                        patience_counter = 0
                    else:
                        patience_counter += 1
                        if patience_counter >= 10:
                            logger.info(f"⏹️  Early stopping at epoch {epoch + 1}")
                            break
                    
                    if (epoch + 1) % 10 == 0:
                        logger.info(f"Epoch {epoch+1:3d}: train_loss={train_loss:.4f}, test_loss={test_loss:.4f}, "
                                  f"acc={test_acc:.4f}, auc={test_auc:.4f}")
            
            self.training_history = history
            
            logger.info(f"✅ Training completed ({epoch + 1} epochs)")
            
            return history
    
    def evaluate(self, X_test: torch.Tensor, y_test: torch.Tensor) -> Dict:
        """
        Evaluate model on test set
        
        Args:
            X_test: Test features
            y_test: Test labels
            
        Returns:
            Evaluation metrics dict
        """
        with LogContext("Evaluating model"):
            self.model.eval()
            
            with torch.no_grad():
                predictions_proba = self.model.predict_proba(X_test).cpu().numpy().flatten()
                predictions = (predictions_proba >= 0.5).astype(int)
                y_true = y_test.cpu().numpy().flatten()
            
            # Metrics
            cm = confusion_matrix(y_true, predictions)
            report = classification_report(y_true, predictions, output_dict=True, zero_division=0)
            
            # Handle AUC
            try:
                auc = roc_auc_score(y_true, predictions_proba)
                fpr, tpr, thresholds = roc_curve(y_true, predictions_proba)
            except:
                auc = 0.0
                fpr, tpr, thresholds = [], [], []
            
            # Extract metrics safely - check various possible keys
            precision = 0.0
            recall = 0.0
            f1 = 0.0
            
            for key in ['1', 1, '1.0', 1.0]:
                if key in report:
                    precision = report[key].get('precision', 0.0)
                    recall = report[key].get('recall', 0.0)
                    f1 = report[key].get('f1-score', 0.0)
                    break
            
            # Format results
            metrics = {
                'accuracy': report.get('accuracy', 0.0),
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'auc': auc,
                'confusion_matrix': cm.tolist(),
                'roc_curve': {
                    'fpr': fpr.tolist() if isinstance(fpr, np.ndarray) else fpr,
                    'tpr': tpr.tolist() if isinstance(tpr, np.ndarray) else tpr,
                    'thresholds': thresholds.tolist() if isinstance(thresholds, np.ndarray) else thresholds
                }
            }
            
            # Log results
            logger.info(f"✅ Evaluation Results:")
            logger.info(f"  Accuracy:  {metrics['accuracy']:.4f}")
            logger.info(f"  Precision: {metrics['precision']:.4f}")
            logger.info(f"  Recall:    {metrics['recall']:.4f}")
            logger.info(f"  F1 Score:  {metrics['f1_score']:.4f}")
            logger.info(f"  AUC:       {metrics['auc']:.4f}")
            
            print("\nClassification Report:")
            print(classification_report(y_true, predictions))
            
            return metrics
    
    def save_checkpoint(self, model_path: Path, scaler_path: Path):
        """
        Save trained model and scaler
        
        Args:
            model_path: Path to save model weights
            scaler_path: Path to save scaler
        """
        model_path.parent.mkdir(parents=True, exist_ok=True)
        scaler_path.parent.mkdir(parents=True, exist_ok=True)
        
        torch.save(self.model.state_dict(), model_path)
        joblib.dump(self.scaler, scaler_path)
        
        logger.info(f"💾 Model saved: {model_path}")
        logger.info(f"💾 Scaler saved: {scaler_path}")
    
    def load_checkpoint(self, model_path: Path, scaler_path: Path):
        """Load trained model and scaler"""
        self.scaler = joblib.load(scaler_path)
        input_dim = len(FEATURE_COLUMNS)
        
        self.model = FCNN(input_dim=input_dim).to(self.device)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        
        logger.info(f"✅ Model loaded: {model_path}")
        logger.info(f"✅ Scaler loaded: {scaler_path}")


class AnomalyDetector:
    """
    Real-time anomaly detection using trained FCNN
    """
    
    def __init__(self, model_path: Path, scaler_path: Path):
        """
        Initialize detector with trained model
        
        Args:
            model_path: Path to trained model weights
            scaler_path: Path to scaler pickle
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Determine input dimension from scaler
        self.scaler = joblib.load(scaler_path)
        input_dim = len(FEATURE_COLUMNS)
        
        self.model = FCNN(input_dim=input_dim).to(self.device)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        
        self.threshold = 0.5
        
        logger.info(f"✅ Anomaly Detector initialized with model from {model_path}")
        logger.info(f"   Input features: {input_dim}")
    
    def detect(self, features: Dict[str, float]) -> Dict:
        """
        Detect anomaly for extracted features
        
        Args:
            features: Dict with 17 ADCS features
            
        Returns:
            Detection result dict with:
            - detected: bool (prob >= 0.5)
            - probability: float (0.0-1.0)
            - severity: str (LOW/MEDIUM/HIGH/CRITICAL)
            - confidence: float (how sure we are)
            - characteristics: list (anomaly types detected)
        """
        # Create feature array in correct order
        feature_array = np.array([[
            features.get(feat, 0.0) for feat in FEATURE_COLUMNS
        ]], dtype=np.float32)
        
        # Normalize
        feature_scaled = self.scaler.transform(feature_array)
        
        # Predict
        with torch.no_grad():
            X_tensor = torch.FloatTensor(feature_scaled).to(self.device)
            probability = self.model.predict_proba(X_tensor).item()
        
        detected = probability >= self.threshold
        
        # Determine severity based on probability
        if probability >= 0.8:
            severity = 'CRITICAL'
        elif probability >= 0.65:
            severity = 'HIGH'
        elif probability >= 0.5:
            severity = 'MEDIUM'
        else:
            severity = 'LOW'
        
        # Extract characteristics for RCA
        characteristics = CharacteristicsExtractor.extract_characteristics(features)
        
        return {
            'detected': detected,
            'probability': float(probability),
            'severity': severity,
            'confidence': float(max(probability, 1 - probability)),
            'characteristics': characteristics
        }


def train_anomaly_detector():
    """
    Main training script
    Trains FCNN on dataset.csv and saves model checkpoint
    """
    print("\n" + "="*80)
    print("ANOMALY DETECTION TRAINING PIPELINE")
    print("="*80)
    
    # Initialize trainer
    trainer = AnomalyDetectionTrainer()
    
    # Prepare data
    X_train, y_train, X_test, y_test = trainer.prepare_data()
    
    # Train model
    history = trainer.train(
        X_train, y_train, X_test, y_test,
        epochs=150,
        batch_size=32,
        learning_rate=0.001
    )
    
    # Evaluate
    metrics = trainer.evaluate(X_test, y_test)
    
    # Save checkpoint
    model_path = Path(settings.DATA_DIR) / 'anomaly_model.pt'
    scaler_path = Path(settings.DATA_DIR) / 'anomaly_scaler.pkl'
    trainer.save_checkpoint(model_path, scaler_path)
    
    print("\n" + "="*80)
    print("✅ TRAINING COMPLETED")
    print("="*80)
    
    return trainer, metrics


if __name__ == '__main__':
    train_anomaly_detector()
