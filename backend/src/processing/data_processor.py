"""Data Processing & Feature Engineering Module"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.impute import SimpleImputer
import joblib
from pathlib import Path

from ..config import settings
from ..utils.logger import get_logger, LogContext

logger = get_logger()


class TelemetryProcessor:
    """Production-grade telemetry data processing pipeline"""
    
    def __init__(self, scaler_type: str = "standard"):
        """
        Initialize processor with scaling strategy
        
        Args:
            scaler_type: Type of scaler ('standard', 'robust', 'minmax')
        """
        self.scaler_type = scaler_type
        self.scaler = self._init_scaler(scaler_type)
        self.imputer = SimpleImputer(strategy='mean')
        self.feature_columns = None
        self.is_fitted = False
        
        logger.info(f"🔧 TelemetryProcessor initialized with {scaler_type} scaling")
    
    def _init_scaler(self, scaler_type: str):
        """Initialize the appropriate scaler"""
        scalers = {
            'standard': StandardScaler(),
            'robust': RobustScaler(),
            'minmax': MinMaxScaler()
        }
        return scalers.get(scaler_type, StandardScaler())
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean telemetry data by handling missing values and outliers
        
        Args:
            df: Input dataframe
            
        Returns:
            Cleaned dataframe
        """
        with LogContext("Cleaning telemetry data"):
            df_clean = df.copy()
            
            # Remove duplicates
            duplicates = df_clean.duplicated().sum()
            if duplicates > 0:
                df_clean = df_clean.drop_duplicates()
                logger.info(f"🗑️  Removed {duplicates} duplicate records")
            
            # Handle infinite values
            numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
            df_clean[numeric_cols] = df_clean[numeric_cols].replace([np.inf, -np.inf], np.nan)
            
            # Log missing value statistics before imputation
            missing_before = df_clean.isnull().sum().sum()
            if missing_before > 0:
                logger.warning(f"⚠️  Found {missing_before} missing values - will impute")
            
            logger.info(f"✅ Data cleaned: {len(df_clean)} records")
            return df_clean
    
    def handle_missing_values(
        self, 
        df: pd.DataFrame, 
        feature_cols: List[str],
        fit: bool = True
    ) -> pd.DataFrame:
        """
        Impute missing values in feature columns
        
        Args:
            df: Input dataframe
            feature_cols: List of feature columns to impute
            fit: Whether to fit the imputer (True for training, False for test)
            
        Returns:
            DataFrame with imputed values
        """
        df_imputed = df.copy()
        
        missing_mask = df_imputed[feature_cols].isnull().sum()
        missing_cols = missing_mask[missing_mask > 0]
        
        if len(missing_cols) > 0:
            logger.warning(f"⚠️  Imputing missing values in {len(missing_cols)} columns")
        
        # Always fit or transform to ensure consistency
        if fit:
            df_imputed[feature_cols] = self.imputer.fit_transform(df_imputed[feature_cols])
        else:
            df_imputed[feature_cols] = self.imputer.transform(df_imputed[feature_cols])
        
        return df_imputed
    
    def remove_outliers(
        self, 
        df: pd.DataFrame, 
        feature_cols: List[str],
        method: str = "iqr",
        threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        Remove outliers using IQR or Z-score method
        
        Args:
            df: Input dataframe
            feature_cols: Feature columns to check for outliers
            method: 'iqr' or 'zscore'
            threshold: IQR multiplier or Z-score threshold
            
        Returns:
            DataFrame with outliers removed
        """
        df_clean = df.copy()
        initial_count = len(df_clean)
        
        if method == "iqr":
            for col in feature_cols:
                Q1 = df_clean[col].quantile(0.25)
                Q3 = df_clean[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                df_clean = df_clean[
                    (df_clean[col] >= lower_bound) & (df_clean[col] <= upper_bound)
                ]
        
        elif method == "zscore":
            from scipy import stats
            z_scores = np.abs(stats.zscore(df_clean[feature_cols]))
            df_clean = df_clean[(z_scores < threshold).all(axis=1)]
        
        removed_count = initial_count - len(df_clean)
        if removed_count > 0:
            logger.info(f"🗑️  Removed {removed_count} outlier records ({removed_count/initial_count*100:.2f}%)")
        
        return df_clean
    
    def fit_scaler(
        self, 
        X: pd.DataFrame, 
        feature_cols: Optional[List[str]] = None
    ):
        """
        Fit the scaler on training data
        
        Args:
            X: Training features
            feature_cols: Optional list of feature columns
        """
        with LogContext("Fitting scaler on training data"):
            if feature_cols is None:
                feature_cols = X.columns.tolist()
            
            self.feature_columns = feature_cols
            self.scaler.fit(X[feature_cols])
            self.is_fitted = True
            
            logger.info(f"✅ Scaler fitted on {len(feature_cols)} features")
    
    def transform(
        self, 
        X: pd.DataFrame, 
        fit: bool = False
    ) -> np.ndarray:
        """
        Transform features using fitted scaler
        
        Args:
            X: Input features
            fit: Whether to fit the scaler first
            
        Returns:
            Scaled feature array
        """
        if self.feature_columns is None:
            self.feature_columns = X.columns.tolist()
        
        if fit or not self.is_fitted:
            self.fit_scaler(X, self.feature_columns)
        
        X_scaled = self.scaler.transform(X[self.feature_columns])
        
        return X_scaled
    
    def fit_transform(self, X: pd.DataFrame) -> np.ndarray:
        """Fit scaler and transform in one step"""
        return self.transform(X, fit=True)
    
    def inverse_transform(self, X_scaled: np.ndarray) -> np.ndarray:
        """
        Inverse transform scaled data back to original scale
        
        Args:
            X_scaled: Scaled features
            
        Returns:
            Original scale features
        """
        if not self.is_fitted:
            raise ValueError("Scaler must be fitted before inverse transform")
        
        return self.scaler.inverse_transform(X_scaled)
    
    def prepare_training_data(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str = 'anomaly'
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare complete training and test datasets
        
        Args:
            train_df: Training dataframe
            test_df: Test dataframe
            feature_cols: Feature column names
            target_col: Target column name
            
        Returns:
            Tuple of (X_train, X_test, y_train, y_test)
        """
        with LogContext("Preparing training data"):
            # Extract features and labels
            X_train = train_df[feature_cols].copy()
            X_test = test_df[feature_cols].copy()
            y_train = train_df[target_col].values
            y_test = test_df[target_col].values
            
            # Handle missing values - fit on train, transform on test
            X_train = self.handle_missing_values(X_train, feature_cols, fit=True)
            X_test = self.handle_missing_values(X_test, feature_cols, fit=False)
            
            # Scale features
            X_train_scaled = self.fit_transform(X_train)
            X_test_scaled = self.transform(X_test)
            
            logger.info(f"✅ Training data prepared:")
            logger.info(f"   X_train: {X_train_scaled.shape}")
            logger.info(f"   X_test: {X_test_scaled.shape}")
            logger.info(f"   y_train anomalies: {y_train.sum()}/{len(y_train)} ({y_train.mean()*100:.2f}%)")
            logger.info(f"   y_test anomalies: {y_test.sum()}/{len(y_test)} ({y_test.mean()*100:.2f}%)")
            
            return X_train_scaled, X_test_scaled, y_train, y_test
    
    def save(self, filepath: Path):
        """Save fitted processor to disk"""
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted processor")
        
        processor_state = {
            'scaler': self.scaler,
            'imputer': self.imputer,
            'scaler_type': self.scaler_type,
            'feature_columns': self.feature_columns,
            'is_fitted': self.is_fitted
        }
        
        joblib.dump(processor_state, filepath)
        logger.info(f"💾 Processor saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: Path):
        """Load fitted processor from disk"""
        processor_state = joblib.load(filepath)
        
        processor = cls(scaler_type=processor_state['scaler_type'])
        processor.scaler = processor_state['scaler']
        processor.imputer = processor_state['imputer']
        processor.feature_columns = processor_state['feature_columns']
        processor.is_fitted = processor_state['is_fitted']
        
        logger.info(f"📂 Processor loaded from {filepath}")
        return processor


class FeatureEngineer:
    """Advanced feature engineering for telemetry data"""
    
    @staticmethod
    def create_rolling_features(
        df: pd.DataFrame,
        value_col: str = 'value',
        windows: List[int] = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        Create rolling window statistical features
        
        Args:
            df: Input dataframe with time-series data
            value_col: Column to compute rolling features on
            windows: List of window sizes
            
        Returns:
            DataFrame with additional rolling features
        """
        df_features = df.copy()
        
        for window in windows:
            df_features[f'rolling_mean_{window}'] = df[value_col].rolling(window).mean()
            df_features[f'rolling_std_{window}'] = df[value_col].rolling(window).std()
            df_features[f'rolling_min_{window}'] = df[value_col].rolling(window).min()
            df_features[f'rolling_max_{window}'] = df[value_col].rolling(window).max()
        
        logger.info(f"✅ Created rolling features for windows: {windows}")
        return df_features
    
    @staticmethod
    def create_lag_features(
        df: pd.DataFrame,
        value_col: str = 'value',
        lags: List[int] = [1, 2, 3, 5, 10]
    ) -> pd.DataFrame:
        """
        Create lagged features
        
        Args:
            df: Input dataframe
            value_col: Column to lag
            lags: List of lag values
            
        Returns:
            DataFrame with lag features
        """
        df_features = df.copy()
        
        for lag in lags:
            df_features[f'lag_{lag}'] = df[value_col].shift(lag)
        
        logger.info(f"✅ Created lag features: {lags}")
        return df_features
