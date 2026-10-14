"""Models Package - Anomaly Detection Models"""
from .fcnn_model import FCNN, FCNNEnsemble
from .fcnn_trainer import FCNNTrainer

__all__ = ["FCNN", "FCNNEnsemble", "FCNNTrainer"]
