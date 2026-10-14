"""
FCNN Model Training Pipeline
Production-grade training with early stopping, checkpointing, and monitoring
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

from ..config import settings
from ..utils.logger import get_logger, LogContext
from .fcnn_model import FCNN

logger = get_logger()


class FCNNTrainer:
    """Production-grade FCNN training pipeline"""
    
    def __init__(
        self,
        model: FCNN,
        device: Optional[str] = None,
        learning_rate: float = 0.001,
        weight_decay: float = 1e-5
    ):
        """
        Initialize trainer
        
        Args:
            model: FCNN model instance
            device: Device to train on ('cuda', 'cpu', or None for auto)
            learning_rate: Learning rate for optimizer
            weight_decay: L2 regularization strength
        """
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = model.to(self.device)
        self.learning_rate = learning_rate
        
        # Optimizer
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5,
            verbose=True
        )
        
        # Loss function (Binary Cross Entropy with class weighting)
        self.criterion = None  # Will be set based on class distribution
        
        # Training history
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'train_acc': [],
            'val_acc': [],
            'learning_rates': []
        }
        
        logger.info(f"🔧 FCNNTrainer initialized on device: {self.device}")
        logger.info(f"📊 Model: {sum(p.numel() for p in model.parameters())} parameters")
    
    def _setup_loss_function(self, y_train: np.ndarray):
        """
        Setup loss function with class weighting for imbalanced data
        
        Args:
            y_train: Training labels
        """
        # Calculate class weights
        n_samples = len(y_train)
        n_positive = y_train.sum()
        n_negative = n_samples - n_positive
        
        # Weight for positive class (anomalies)
        pos_weight = n_negative / n_positive if n_positive > 0 else 1.0
        pos_weight = torch.tensor([pos_weight], device=self.device)
        
        self.criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        
        logger.info(f"⚖️  Class distribution: Normal={n_negative}, Anomaly={n_positive}")
        logger.info(f"⚖️  Positive class weight: {pos_weight.item():.2f}")
    
    def _create_dataloaders(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        batch_size: int = 32
    ) -> Tuple[DataLoader, Optional[DataLoader]]:
        """
        Create PyTorch DataLoaders
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            batch_size: Batch size
            
        Returns:
            Tuple of (train_loader, val_loader)
        """
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train)
        y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
        
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0,  # Windows compatibility
            pin_memory=True if self.device == 'cuda' else False
        )
        
        val_loader = None
        if X_val is not None and y_val is not None:
            X_val_tensor = torch.FloatTensor(X_val)
            y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1)
            
            val_dataset = TensorDataset(X_val_tensor, y_val_tensor)
            val_loader = DataLoader(
                val_dataset,
                batch_size=batch_size,
                shuffle=False,
                num_workers=0,
                pin_memory=True if self.device == 'cuda' else False
            )
        
        return train_loader, val_loader
    
    def train_epoch(self, train_loader: DataLoader) -> Tuple[float, float]:
        """
        Train for one epoch
        
        Args:
            train_loader: Training data loader
            
        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        
        for batch_X, batch_y in train_loader:
            batch_X = batch_X.to(self.device)
            batch_y = batch_y.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(batch_X)
            loss = self.criterion(outputs, batch_y)
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            # Track metrics
            total_loss += loss.item()
            predictions = torch.sigmoid(outputs) >= 0.5
            correct += (predictions == batch_y).sum().item()
            total += batch_y.size(0)
        
        avg_loss = total_loss / len(train_loader)
        accuracy = correct / total
        
        return avg_loss, accuracy
    
    def validate(self, val_loader: DataLoader) -> Tuple[float, float]:
        """
        Validate model
        
        Args:
            val_loader: Validation data loader
            
        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)
                
                outputs = self.model(batch_X)
                loss = self.criterion(outputs, batch_y)
                
                total_loss += loss.item()
                predictions = torch.sigmoid(outputs) >= 0.5
                correct += (predictions == batch_y).sum().item()
                total += batch_y.size(0)
        
        avg_loss = total_loss / len(val_loader)
        accuracy = correct / total
        
        return avg_loss, accuracy
    
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 100,
        batch_size: int = 32,
        early_stopping_patience: int = 10,
        checkpoint_dir: Optional[Path] = None
    ) -> Dict:
        """
        Train the model with early stopping and checkpointing
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            epochs: Maximum number of epochs
            batch_size: Batch size
            early_stopping_patience: Patience for early stopping
            checkpoint_dir: Directory to save checkpoints
            
        Returns:
            Training history dictionary
        """
        with LogContext("Training FCNN model", epochs=epochs, batch_size=batch_size):
            # Setup loss function
            self._setup_loss_function(y_train)
            
            # Create dataloaders
            train_loader, val_loader = self._create_dataloaders(
                X_train, y_train, X_val, y_val, batch_size
            )
            
            # Early stopping setup
            best_val_loss = float('inf')
            patience_counter = 0
            best_model_state = None
            
            # Checkpoint directory
            if checkpoint_dir:
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            # Training loop
            for epoch in range(1, epochs + 1):
                # Train
                train_loss, train_acc = self.train_epoch(train_loader)
                self.history['train_loss'].append(train_loss)
                self.history['train_acc'].append(train_acc)
                
                # Validate
                if val_loader:
                    val_loss, val_acc = self.validate(val_loader)
                    self.history['val_loss'].append(val_loss)
                    self.history['val_acc'].append(val_acc)
                    
                    # Learning rate scheduling
                    self.scheduler.step(val_loss)
                    
                    # Early stopping check
                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        patience_counter = 0
                        best_model_state = self.model.state_dict().copy()
                        
                        # Save checkpoint
                        if checkpoint_dir:
                            checkpoint_path = checkpoint_dir / f"best_model_epoch_{epoch}.pt"
                            self.save_checkpoint(checkpoint_path, epoch, val_loss, val_acc)
                    else:
                        patience_counter += 1
                    
                    # Log progress
                    if epoch % 10 == 0 or epoch == 1:
                        logger.info(
                            f"Epoch {epoch}/{epochs} - "
                            f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f} | "
                            f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f} | "
                            f"LR: {self.optimizer.param_groups[0]['lr']:.6f}"
                        )
                    
                    # Early stopping
                    if patience_counter >= early_stopping_patience:
                        logger.info(f"⏹️  Early stopping triggered at epoch {epoch}")
                        break
                else:
                    # No validation set
                    if epoch % 10 == 0 or epoch == 1:
                        logger.info(
                            f"Epoch {epoch}/{epochs} - "
                            f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}"
                        )
                
                # Track learning rate
                self.history['learning_rates'].append(self.optimizer.param_groups[0]['lr'])
            
            # Restore best model
            if best_model_state:
                self.model.load_state_dict(best_model_state)
                logger.info(f"✅ Restored best model with val_loss={best_val_loss:.4f}")
            
            logger.info("✅ Training completed")
            return self.history
    
    def save_checkpoint(
        self,
        filepath: Path,
        epoch: int,
        val_loss: float,
        val_acc: float
    ):
        """Save model checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'val_loss': val_loss,
            'val_acc': val_acc,
            'history': self.history
        }
        torch.save(checkpoint, filepath)
        logger.debug(f"💾 Checkpoint saved: {filepath}")
    
    def load_checkpoint(self, filepath: Path):
        """Load model checkpoint"""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.history = checkpoint['history']
        logger.info(f"📂 Checkpoint loaded: {filepath}")
        return checkpoint
    
    def save_model(self, filepath: Path, metadata: Optional[Dict] = None):
        """Save complete model with metadata"""
        model_package = {
            'model_state_dict': self.model.state_dict(),
            'model_config': {
                'input_dim': self.model.input_dim,
                'hidden_layers': self.model.hidden_layers,
                'dropout_rate': self.model.dropout_rate,
                'use_batch_norm': self.model.use_batch_norm,
                'output_dim': self.model.output_dim
            },
            'history': self.history,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        torch.save(model_package, filepath)
        logger.info(f"💾 Model saved: {filepath}")
    
    @classmethod
    def load_model(cls, filepath: Path, device: Optional[str] = None) -> Tuple[FCNN, 'FCNNTrainer']:
        """Load model from file"""
        model_package = torch.load(filepath, map_location=device or 'cpu')
        
        # Recreate model
        model = FCNN(**model_package['model_config'])
        model.load_state_dict(model_package['model_state_dict'])
        
        # Create trainer
        trainer = cls(model, device=device)
        trainer.history = model_package['history']
        trainer.metadata = model_package.get('metadata', {})
        
        logger.info(f"📂 Model loaded: {filepath}")
        return model, trainer
