"""Data Ingestion Module - ESA OPS-SAT Telemetry"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from ..config import settings
from ..utils.logger import get_logger, LogContext
from ..processing.feature_extractor import SegmentFeatureExtractor, FEATURE_COLUMNS

logger = get_logger()


class TelemetryIngestor:
    """Ingest and validate ESA OPS-SAT ADCS telemetry data"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or settings.DATA_DIR
        self.dataset_path = self.data_dir / settings.DATASET_CSV
        self.segments_path = self.data_dir / settings.SEGMENTS_CSV
        
        # Initialize feature extractor
        self.feature_extractor = SegmentFeatureExtractor(verbose=False)
        
        logger.info(f"📡 Telemetry Ingestor initialized - Data directory: {self.data_dir}")
    
    def extract_features_from_segments(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract 17 ML-ready features from raw segment time-series data.
        
        This maps segments.csv (raw readings) → dataset.csv (features).
        
        Args:
            df: Raw segments dataframe (from segments.csv)
            
        Returns:
            DataFrame with extracted 17 features
        """
        with LogContext("Extracting features from raw segments"):
            features_df = self.feature_extractor.extract_features_from_dataframe(df)
            logger.info(f"✅ Extracted features for {len(features_df)} segments")
            return features_df
    
    def extract_features_for_segment(
        self,
        segment_df: pd.DataFrame,
        segment_id: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Extract 17 features for a single segment.
        
        Args:
            segment_df: DataFrame with readings for one segment
            segment_id: Optional segment identifier
            
        Returns:
            Dictionary with 17 features
        """
        if 'segment' in segment_df.columns:
            segment_id = segment_df['segment'].iloc[0]
        
        values = segment_df['value'].values
        timestamps = segment_df['timestamp'].values if 'timestamp' in segment_df.columns else None
        channel = segment_df['channel'].iloc[0] if 'channel' in segment_df.columns else None
        
        features = self.feature_extractor.extract_features_from_segment(
            values=values,
            timestamps=timestamps,
            segment_id=segment_id,
            channel=channel
        )
        
        if 'anomaly' in segment_df.columns:
            features['anomaly'] = int(segment_df['anomaly'].iloc[0])
        
        return features
    
    def verify_feature_extraction(
        self,
        extracted_df: pd.DataFrame,
        reference_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, any]:
        """
        Verify that extracted features match expected schema.
        
        Args:
            extracted_df: Extracted features dataframe
            reference_df: Optional reference (dataset.csv) for comparison
            
        Returns:
            Validation report
        """
        return self.feature_extractor.verify_feature_extraction(extracted_df, reference_df)
    
    def load_dataset(self) -> pd.DataFrame:
        """
        Load pre-computed segment features dataset
        
        Returns:
            DataFrame with segment-level features and labels
        """
        with LogContext("Loading dataset features", file=settings.DATASET_CSV):
            df = pd.read_csv(self.dataset_path)
            logger.info(f"✅ Loaded {len(df)} segments with {df.shape[1]} features")
            logger.info(f"📊 Anomaly distribution: {df['anomaly'].value_counts().to_dict()}")
            logger.info(f"📊 Train/Test split: {df['train'].value_counts().to_dict()}")
            
            return df
    
    def load_segments(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Load raw time-series telemetry segments
        
        Args:
            limit: Optional limit on number of rows to load
            
        Returns:
            DataFrame with timestamp-based telemetry readings
        """
        with LogContext("Loading raw segments", file=settings.SEGMENTS_CSV):
            if limit:
                df = pd.read_csv(self.segments_path, nrows=limit)
            else:
                df = pd.read_csv(self.segments_path)
            
            # Parse timestamps
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            logger.info(f"✅ Loaded {len(df)} telemetry readings")
            logger.info(f"📅 Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            logger.info(f"📡 Channels: {df['channel'].unique().tolist()}")
            
            return df
    
    def get_channel_data(self, df: pd.DataFrame, channel: str) -> pd.DataFrame:
        """
        Extract data for a specific channel
        
        Args:
            df: Segments dataframe
            channel: Channel identifier
            
        Returns:
            Filtered dataframe for the channel
        """
        channel_df = df[df['channel'] == channel].copy()
        logger.info(f"📡 Channel {channel}: {len(channel_df)} readings")
        return channel_df
    
    def get_segment_window(
        self, 
        df: pd.DataFrame, 
        segment_id: int
    ) -> pd.DataFrame:
        """
        Get all readings for a specific segment
        
        Args:
            df: Segments dataframe
            segment_id: Segment identifier
            
        Returns:
            DataFrame with readings for the segment
        """
        segment_df = df[df['segment'] == segment_id].copy()
        return segment_df
    
    def validate_data(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Validate telemetry data quality
        
        Args:
            df: Input dataframe
            
        Returns:
            Validation report dictionary
        """
        with LogContext("Validating telemetry data"):
            report = {
                'total_records': len(df),
                'missing_values': df.isnull().sum().to_dict(),
                'duplicate_records': df.duplicated().sum(),
                'channels': df['channel'].nunique() if 'channel' in df.columns else None,
                'segments': df['segment'].nunique() if 'segment' in df.columns else None,
                'anomaly_ratio': df['anomaly'].mean() if 'anomaly' in df.columns else None,
                'data_types': df.dtypes.to_dict(),
                'value_ranges': {}
            }
            
            # Check value ranges for numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                report['value_ranges'][col] = {
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'mean': float(df[col].mean()),
                    'std': float(df[col].std())
                }
            
            # Log warnings
            if report['duplicate_records'] > 0:
                logger.warning(f"⚠️  Found {report['duplicate_records']} duplicate records")
            
            missing_total = sum(report['missing_values'].values())
            if missing_total > 0:
                logger.warning(f"⚠️  Found {missing_total} missing values")
            
            logger.info(f"✅ Data validation completed")
            return report
    
    def get_train_test_split(
        self, 
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split data into train and test sets based on 'train' column
        
        Args:
            df: Input dataframe with 'train' column
            
        Returns:
            Tuple of (train_df, test_df)
        """
        train_df = df[df['train'] == 1].copy()
        test_df = df[df['train'] == 0].copy()
        
        logger.info(f"📊 Train set: {len(train_df)} samples ({len(train_df[train_df['anomaly']==1])} anomalies)")
        logger.info(f"📊 Test set: {len(test_df)} samples ({len(test_df[test_df['anomaly']==1])} anomalies)")
        
        return train_df, test_df
    
    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Extract feature column names (excluding metadata and labels)
        
        Args:
            df: Input dataframe
            
        Returns:
            List of feature column names
        """
        exclude_cols = ['segment', 'anomaly', 'train', 'channel', 'sampling', 'timestamp', 'label']
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        logger.info(f"🔍 Identified {len(feature_cols)} feature columns")
        return feature_cols
    
    async def stream_telemetry(
        self, 
        batch_size: int = 100, 
        channel: Optional[str] = None
    ):
        """
        Simulate real-time telemetry streaming (for production deployment)
        
        Args:
            batch_size: Number of records per batch
            channel: Optional channel filter
            
        Yields:
            Batches of telemetry data
        """
        df = self.load_segments()
        
        if channel:
            df = df[df['channel'] == channel]
        
        total_batches = len(df) // batch_size + 1
        logger.info(f"🌊 Starting telemetry stream - {total_batches} batches of {batch_size} records")
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            yield batch
            logger.debug(f"📤 Streamed batch {i//batch_size + 1}/{total_batches}")


# Convenience function for quick data loading
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Quick loader for dataset and segments
    
    Returns:
        Tuple of (dataset_df, segments_df)
    """
    ingestor = TelemetryIngestor()
    dataset_df = ingestor.load_dataset()
    segments_df = ingestor.load_segments(limit=10000)  # Load first 10K for quick start
    
    return dataset_df, segments_df
