"""
Quick script to create and save data processor without full model training
"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings
from src.ingestion import TelemetryIngestor
from src.processing import TelemetryProcessor

def main():
    print("📡 Loading dataset...")
    ingestor = TelemetryIngestor()
    dataset_df = ingestor.load_dataset()
    
    print("✂️ Splitting data...")
    train_df, test_df = ingestor.get_train_test_split(dataset_df)
    
    print("🔧 Creating processor...")
    processor = TelemetryProcessor(scaler_type='standard')
    
    # Get feature columns
    feature_cols = ingestor.get_feature_columns(dataset_df)
    
    # Prepare data (this fits the scaler)
    X_train, X_test, y_train, y_test = processor.prepare_training_data(
        train_df=train_df,
        test_df=test_df,
        feature_cols=feature_cols,
        target_col='anomaly'
    )
    
    print(f"✅ Processor fitted with {len(feature_cols)} features")
    
    # Save processor
    processor_path = settings.MODELS_DIR / "trained" / "data_processor.pkl"
    processor.save(processor_path)
    print(f"💾 Data processor saved: {processor_path}")
    print("✅ Done!")

if __name__ == "__main__":
    main()
