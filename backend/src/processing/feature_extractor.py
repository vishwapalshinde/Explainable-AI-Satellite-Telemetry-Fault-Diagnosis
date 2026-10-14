"""
Feature Extraction Module - Convert raw ADCS telemetry to ML-ready features

Extracts 17 statistical features from raw time-series segments for anomaly detection.
This module bridges the gap between segments.csv (raw readings) and dataset.csv (features).
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy import signal, stats
from scipy.ndimage import uniform_filter1d
from datetime import datetime

from ..utils.logger import get_logger, LogContext

logger = get_logger()

# Feature column names in correct order for ML model
FEATURE_COLUMNS = [
    'duration', 'len', 'mean', 'var', 'std', 'kurtosis', 'skew',
    'n_peaks', 'smooth10_n_peaks', 'smooth20_n_peaks',
    'diff_peaks', 'diff2_peaks', 'diff_var', 'diff2_var',
    'gaps_squared', 'len_weighted', 'var_div_duration', 'var_div_len'
]


class SegmentFeatureExtractor:
    """
    Extract 17 statistical features from raw segment time-series data.
    
    Maps from segments.csv (raw readings) to dataset.csv (pre-computed features).
    
    Features include:
    - Temporal: duration, len
    - Statistical: mean, var, std, kurtosis, skew
    - Peak detection: n_peaks (3 variants), diff_peaks, diff2_peaks
    - Derivative: diff_var, diff2_var
    - Engineered: gaps_squared, len_weighted, var_div_duration, var_div_len
    """
    
    def __init__(self, verbose: bool = False):
        """Initialize feature extractor"""
        self.verbose = verbose
        self.extraction_stats = {}
    
    def extract_features_from_segment(
        self,
        values: np.ndarray,
        timestamps: Optional[List[datetime]] = None,
        segment_id: Optional[int] = None,
        channel: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Extract 17 features from a segment of raw telemetry data.
        
        Args:
            values: Array of raw measurement values
            timestamps: Optional list of datetime objects for temporal features
            segment_id: Optional segment identifier for tracking
            channel: Optional channel name for metadata
            
        Returns:
            Dictionary with 17 feature names and their computed values
            
        Example:
            >>> values = np.array([-2.15e-05, -2.05e-05, -2.11e-05, ...])
            >>> features = extractor.extract_features_from_segment(values)
            >>> print(features['mean'], features['n_peaks'])
            8.53e-07, 4
        """
        
        # Input validation
        if len(values) < 3:
            logger.warning(f"⚠️  Segment {segment_id} has fewer than 3 values")
            return self._get_null_features()
        
        values = np.array(values, dtype=float)
        
        # Remove any NaN values
        valid_mask = ~np.isnan(values)
        values = values[valid_mask]
        
        if len(values) < 3:
            logger.warning(f"⚠️  Segment {segment_id} has fewer than 3 valid values after NaN removal")
            return self._get_null_features()
        
        try:
            features = {}
            
            # ============ 1. TEMPORAL FEATURES ============
            
            if timestamps is not None and len(timestamps) > 1:
                timestamps = pd.to_datetime(timestamps)
                duration = (timestamps[-1] - timestamps[0]).total_seconds()
            else:
                # If no timestamps, assume 1Hz sampling
                duration = len(values) - 1
            
            n_points = len(values)
            
            features['duration'] = float(max(duration, 1.0))  # Avoid 0 division later
            features['len'] = float(n_points)
            
            # ============ 2. STATISTICAL FEATURES ============
            
            features['mean'] = float(np.mean(values))
            features['var'] = float(np.var(values))
            features['std'] = float(np.std(values))
            
            # Handle edge cases
            if len(values) >= 4:
                features['kurtosis'] = float(stats.kurtosis(values))
                features['skew'] = float(stats.skew(values))
            else:
                features['kurtosis'] = 0.0
                features['skew'] = 0.0
            
            # ============ 3. PEAK DETECTION FEATURES ============
            
            # Original signal peaks
            peaks, _ = signal.find_peaks(values)
            features['n_peaks'] = float(len(peaks))
            
            # Smoothed signal peaks (10-point window)
            if len(values) >= 10:
                smoothed_10 = uniform_filter1d(values, size=10, mode='nearest')
                peaks_smooth10, _ = signal.find_peaks(smoothed_10)
                features['smooth10_n_peaks'] = float(len(peaks_smooth10))
            else:
                features['smooth10_n_peaks'] = 0.0
            
            # Smoothed signal peaks (20-point window)
            if len(values) >= 20:
                smoothed_20 = uniform_filter1d(values, size=20, mode='nearest')
                peaks_smooth20, _ = signal.find_peaks(smoothed_20)
                features['smooth20_n_peaks'] = float(len(peaks_smooth20))
            else:
                features['smooth20_n_peaks'] = 0.0
            
            # ============ 4. DERIVATIVE FEATURES ============
            
            # First derivative
            diff_1 = np.diff(values, n=1)
            
            if len(diff_1) >= 3:
                peaks_diff, _ = signal.find_peaks(diff_1)
                features['diff_peaks'] = float(len(peaks_diff))
            else:
                features['diff_peaks'] = 0.0
            
            features['diff_var'] = float(np.var(diff_1)) if len(diff_1) > 0 else 0.0
            
            # Second derivative
            diff_2 = np.diff(values, n=2)
            
            if len(diff_2) >= 3:
                peaks_diff2, _ = signal.find_peaks(diff_2)
                features['diff2_peaks'] = float(len(peaks_diff2))
            else:
                features['diff2_peaks'] = 0.0
            
            features['diff2_var'] = float(np.var(diff_2)) if len(diff_2) > 0 else 0.0
            
            # ============ 5. ENGINEERED FEATURES ============
            
            features['gaps_squared'] = float(duration)  # Intentional: duration, not squared
            features['len_weighted'] = float(n_points)
            
            # Variance ratios (avoid division by zero)
            if features['duration'] > 0:
                features['var_div_duration'] = features['var'] / features['duration']
            else:
                features['var_div_duration'] = 0.0
            
            if features['len'] > 0:
                features['var_div_len'] = features['var'] / features['len']
            else:
                features['var_div_len'] = 0.0
            
            # Add metadata if provided
            if segment_id is not None:
                features['segment'] = float(segment_id)
            if channel is not None:
                features['channel'] = channel
            
            # Verify all 17 features are present
            assert len([f for f in features if f in FEATURE_COLUMNS]) == len(FEATURE_COLUMNS), \
                f"Missing features: {set(FEATURE_COLUMNS) - set(features.keys())}"
            
            if self.verbose:
                logger.debug(f"✅ Extracted 17 features from segment {segment_id}")
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error extracting features from segment {segment_id}: {str(e)}")
            return self._get_null_features()
    
    def extract_features_from_dataframe(
        self,
        df: pd.DataFrame,
        group_by: str = 'segment'
    ) -> pd.DataFrame:
        """
        Extract features from all segments in a dataframe.
        
        Args:
            df: DataFrame with raw telemetry data (from segments.csv)
            group_by: Column to group by (default: 'segment')
            
        Returns:
            DataFrame with extracted features (schema matches dataset.csv)
            
        Example:
            >>> segments_df = pd.read_csv('segments.csv')
            >>> features_df = extractor.extract_features_from_dataframe(segments_df)
            >>> features_df.to_csv('extracted_features.csv', index=False)
        """
        
        with LogContext(f"Extracting features from {len(df)} raw readings"):
            extracted_features = []
            
            # Group by segment
            grouped = df.groupby(group_by)
            total_segments = len(grouped)
            
            for idx, (segment_id, segment_df) in enumerate(grouped):
                if idx % 100 == 0 and idx > 0:
                    logger.info(f"🔄 Processed {idx}/{total_segments} segments")
                
                # Sort by timestamp to ensure chronological order
                if 'timestamp' in segment_df.columns:
                    segment_df = segment_df.sort_values('timestamp')
                
                values = segment_df['value'].values
                timestamps = segment_df['timestamp'].values if 'timestamp' in segment_df.columns else None
                channel = segment_df['channel'].iloc[0] if 'channel' in segment_df.columns else None
                anomaly = segment_df['anomaly'].iloc[0] if 'anomaly' in segment_df.columns else None
                
                # Extract features
                features = self.extract_features_from_segment(
                    values=values,
                    timestamps=timestamps,
                    segment_id=segment_id,
                    channel=channel
                )
                
                # Add ground truth label if present
                if anomaly is not None:
                    features['anomaly'] = int(anomaly)
                
                extracted_features.append(features)
            
            logger.info(f"✅ Extracted features from {len(extracted_features)} segments")
            
            # Convert to DataFrame
            features_df = pd.DataFrame(extracted_features)
            
            # Reorder columns to match dataset.csv schema
            column_order = FEATURE_COLUMNS + ['segment']
            if 'channel' in features_df.columns:
                column_order.append('channel')
            if 'anomaly' in features_df.columns:
                column_order.append('anomaly')
            
            # Only include columns that exist
            column_order = [col for col in column_order if col in features_df.columns]
            features_df = features_df[column_order]
            
            # Print summary statistics
            logger.info(f"📊 Feature statistics:")
            for feat in FEATURE_COLUMNS:
                if feat in features_df.columns:
                    mean_val = features_df[feat].mean()
                    std_val = features_df[feat].std()
                    logger.info(f"  {feat:20s}: μ={mean_val:12.4e}, σ={std_val:12.4e}")
            
            return features_df
    
    def verify_feature_extraction(
        self,
        extracted_df: pd.DataFrame,
        reference_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, any]:
        """
        Verify extracted features match expected schema and statistics.
        
        Args:
            extracted_df: DataFrame with extracted features
            reference_df: Optional reference features from dataset.csv to compare against
            
        Returns:
            Validation report dictionary
        """
        
        with LogContext("Verifying feature extraction"):
            report = {
                'status': 'valid',
                'issues': [],
                'features_found': len(extracted_df.columns),
                'samples': len(extracted_df)
            }
            
            # Check all 17 features are present
            missing_features = set(FEATURE_COLUMNS) - set(extracted_df.columns)
            if missing_features:
                report['status'] = 'invalid'
                report['issues'].append(f"Missing features: {missing_features}")
            
            # Check for NaN values
            nan_counts = extracted_df.isnull().sum()
            if nan_counts.sum() > 0:
                report['status'] = 'warning'
                report['issues'].append(f"Found {nan_counts.sum()} NaN values")
            
            # Check value ranges
            value_ranges = {}
            for feat in FEATURE_COLUMNS:
                if feat in extracted_df.columns:
                    value_ranges[feat] = {
                        'min': float(extracted_df[feat].min()),
                        'max': float(extracted_df[feat].max()),
                        'mean': float(extracted_df[feat].mean()),
                        'std': float(extracted_df[feat].std())
                    }
            report['value_ranges'] = value_ranges
            
            # Compare with reference if provided
            if reference_df is not None:
                comparison = {}
                for feat in FEATURE_COLUMNS:
                    if feat in reference_df.columns:
                        ref_mean = reference_df[feat].mean()
                        ext_mean = extracted_df[feat].mean() if feat in extracted_df.columns else 0
                        
                        # Calculate relative error
                        if ref_mean != 0:
                            rel_error = abs(ext_mean - ref_mean) / abs(ref_mean)
                        else:
                            rel_error = abs(ext_mean)
                        
                        comparison[feat] = {
                            'reference_mean': float(ref_mean),
                            'extracted_mean': float(ext_mean),
                            'relative_error': float(rel_error)
                        }
                
                report['comparison_with_reference'] = comparison
            
            # Log results
            if report['status'] == 'valid':
                logger.info(f"✅ Feature extraction validated successfully")
            else:
                logger.warning(f"⚠️  Feature extraction has issues: {report['issues']}")
            
            return report
    
    def _get_null_features(self) -> Dict[str, float]:
        """Return feature dict with all zeros (for invalid segments)"""
        return {feat: 0.0 for feat in FEATURE_COLUMNS}


def batch_extract_features(
    segments_csv_path: str,
    output_csv_path: Optional[str] = None,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """
    Convenience function to extract features from segments.csv in batch.
    
    Args:
        segments_csv_path: Path to segments.csv file
        output_csv_path: Optional path to save extracted features
        limit: Optional row limit for testing
        
    Returns:
        DataFrame with extracted features
        
    Example:
        >>> features_df = batch_extract_features('data/segments.csv', 'data/features.csv')
        >>> print(features_df.shape)
        (2125, 17)
    """
    
    # Load segments
    df = pd.read_csv(segments_csv_path, nrows=limit)
    
    # Extract features
    extractor = SegmentFeatureExtractor(verbose=True)
    features_df = extractor.extract_features_from_dataframe(df)
    
    # Save if requested
    if output_csv_path:
        features_df.to_csv(output_csv_path, index=False)
        logger.info(f"💾 Saved extracted features to {output_csv_path}")
    
    return features_df


if __name__ == '__main__':
    """Quick test of feature extraction"""
    
    # Test with synthetic data
    print("🧪 Testing feature extraction with synthetic data...")
    
    test_values = np.sin(np.linspace(0, 4*np.pi, 280)) + np.random.normal(0, 0.01, 280)
    test_timestamps = pd.date_range('2022-06-01 23:42:54', periods=280, freq='1S')
    
    extractor = SegmentFeatureExtractor(verbose=True)
    features = extractor.extract_features_from_segment(
        test_values,
        test_timestamps,
        segment_id=1,
        channel='CADC0872'
    )
    
    print("\n✅ Extracted features:")
    for feat_name in FEATURE_COLUMNS:
        if feat_name in features:
            print(f"  {feat_name:20s}: {features[feat_name]:12.4e}")
