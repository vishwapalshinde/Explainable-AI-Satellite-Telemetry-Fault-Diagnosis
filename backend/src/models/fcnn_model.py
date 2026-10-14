"""
Fully Connected Neural Network (FCNN) for Anomaly Detection
Production-grade PyTorch implementation with Dropout & Batch Normalization
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Optional


class FCNN(nn.Module):
    """
    Fully Connected Neural Network with Dropout and Batch Normalization
    Optimized for satellite telemetry anomaly detection
    """
    
    def __init__(
        self,
        input_dim: int,
        hidden_layers: List[int] = [128, 64, 32],
        dropout_rate: float = 0.3,
        use_batch_norm: bool = True,
        output_dim: int = 1
    ):
        """
        Initialize FCNN architecture
        
        Args:
            input_dim: Number of input features
            hidden_layers: List of hidden layer sizes
            dropout_rate: Dropout probability
            use_batch_norm: Whether to use batch normalization
            output_dim: Number of output classes (1 for binary classification)
        """
        super(FCNN, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_layers = hidden_layers
        self.dropout_rate = dropout_rate
        self.use_batch_norm = use_batch_norm
        self.output_dim = output_dim
        
        # Build layers
        layers = []
        prev_dim = input_dim
        
        for i, hidden_dim in enumerate(hidden_layers):
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
        layers.append(nn.Linear(prev_dim, output_dim))
        
        # Combine into sequential model
        self.network = nn.Sequential(*layers)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize network weights using Xavier initialization"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.BatchNorm1d):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: Input tensor [batch_size, input_dim]
            
        Returns:
            Output logits [batch_size, output_dim]
        """
        return self.network(x)
    
    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """
        Get probability predictions
        
        Args:
            x: Input tensor
            
        Returns:
            Probability predictions
        """
        logits = self.forward(x)
        return torch.sigmoid(logits)
    
    def predict(self, x: torch.Tensor, threshold: float = 0.5) -> torch.Tensor:
        """
        Get binary predictions
        
        Args:
            x: Input tensor
            threshold: Classification threshold
            
        Returns:
            Binary predictions (0 or 1)
        """
        proba = self.predict_proba(x)
        return (proba >= threshold).long()
    
    def get_model_summary(self) -> str:
        """Get model architecture summary"""
        total_params = sum(p.numel() for p in self.parameters())
        trainable_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        
        summary = f"""
        ╔═══════════════════════════════════════════════════════════╗
        ║              FCNN Model Architecture                      ║
        ╠═══════════════════════════════════════════════════════════╣
        ║ Input Dimension:         {self.input_dim:<30} ║
        ║ Hidden Layers:           {str(self.hidden_layers):<30} ║
        ║ Dropout Rate:            {self.dropout_rate:<30} ║
        ║ Batch Normalization:     {self.use_batch_norm:<30} ║
        ║ Output Dimension:        {self.output_dim:<30} ║
        ║                                                           ║
        ║ Total Parameters:        {total_params:<30} ║
        ║ Trainable Parameters:    {trainable_params:<30} ║
        ╚═══════════════════════════════════════════════════════════╝
        """
        return summary


class FCNNEnsemble(nn.Module):
    """Ensemble of FCNN models for robust predictions"""
    
    def __init__(
        self,
        input_dim: int,
        num_models: int = 5,
        hidden_layers: List[int] = [128, 64, 32],
        dropout_rate: float = 0.3
    ):
        super(FCNNEnsemble, self).__init__()
        
        self.models = nn.ModuleList([
            FCNN(
                input_dim=input_dim,
                hidden_layers=hidden_layers,
                dropout_rate=dropout_rate
            )
            for _ in range(num_models)
        ])
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Average predictions from all models"""
        predictions = [model(x) for model in self.models]
        return torch.mean(torch.stack(predictions), dim=0)
    
    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Get averaged probability predictions"""
        logits = self.forward(x)
        return torch.sigmoid(logits)
