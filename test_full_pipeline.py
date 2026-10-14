"""
End-to-End Pipeline Test: Feature Extraction → Anomaly Detection → Root Cause Analysis

Tests the complete fault diagnosis pipeline with real data.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from backend.src.ingestion.telemetry_ingestor import TelemetryIngestor
from backend.src.models.anomaly_detector import AnomalyDetector
from backend.src.knowledge_graph.kg_builder import ADCSKnowledgeGraph


def test_end_to_end_pipeline():
    """
    Complete end-to-end test of the fault diagnosis system
    """
    print("\n" + "="*80)
    print("END-TO-END FAULT DIAGNOSIS PIPELINE TEST")
    print("="*80)
    
    # ============ STEP 1: Load Data ============
    print("\n[1/6] Loading telemetry data...")
    ingestor = TelemetryIngestor()
    
    # Load segments (use first 10,000 readings for speed)
    segments_df = ingestor.load_segments(limit=10000)
    print(f"✅ Loaded {len(segments_df)} raw telemetry readings")
    print(f"   Unique segments: {segments_df['segment'].nunique()}")
    print(f"   Channels: {segments_df['channel'].unique().tolist()}")
    
    # ============ STEP 2: Initialize Components ============
    print("\n[2/6] Initializing system components...")
    
    # Load trained anomaly detector
    model_path = Path('dataset/anomaly_model.pt')
    scaler_path = Path('dataset/anomaly_scaler.pkl')
    
    if not model_path.exists() or not scaler_path.exists():
        print("❌ ERROR: Trained model not found. Run train_anomaly_model.py first.")
        return False
    
    detector = AnomalyDetector(model_path, scaler_path)
    print(f"✅ Anomaly detector loaded")
    
    # Build knowledge graph
    kg = ADCSKnowledgeGraph()
    kg.build_adcs_ontology()
    print(f"✅ Knowledge graph built: {kg.graph.number_of_nodes()} nodes, {kg.graph.number_of_edges()} edges")
    
    # ============ STEP 3: Test on Anomalous Segments ============
    print("\n[3/6] Testing on anomalous segments from dataset...")
    
    # Get segments marked as anomalous in the dataset
    anomalous_segments = segments_df[segments_df['anomaly'] == 1]['segment'].unique()
    print(f"   Found {len(anomalous_segments)} segments with ground-truth anomalies")
    
    if len(anomalous_segments) == 0:
        print("⚠️  No anomalous segments in loaded data. Using first segment as test.")
        test_segment_ids = [segments_df['segment'].iloc[0]]
    else:
        # Test first 5 anomalous segments
        test_segment_ids = anomalous_segments[:5]
    
    # ============ STEP 4: Process Each Test Segment ============
    print(f"\n[4/6] Processing {len(test_segment_ids)} test segments...\n")
    
    results = []
    
    for idx, segment_id in enumerate(test_segment_ids, 1):
        print(f"\n{'─'*80}")
        print(f"TEST CASE {idx}/{len(test_segment_ids)}: Segment {segment_id}")
        print(f"{'─'*80}")
        
        # Get segment data
        segment_data = segments_df[segments_df['segment'] == segment_id]
        channel = segment_data['channel'].iloc[0]
        ground_truth_anomaly = segment_data['anomaly'].iloc[0]
        
        print(f"\n  Segment Info:")
        print(f"    Channel: {channel}")
        print(f"    Readings: {len(segment_data)}")
        print(f"    Ground Truth: {'ANOMALY' if ground_truth_anomaly == 1 else 'NORMAL'}")
        print(f"    Time span: {segment_data['timestamp'].min()} to {segment_data['timestamp'].max()}")
        
        # Step 4a: Extract features
        print(f"\n  [4a] Extracting 17 features...")
        features = ingestor.extract_features_for_segment(segment_data, segment_id=segment_id)
        
        print(f"    ✅ Features extracted:")
        print(f"       Duration: {features['duration']:.2f}s, Length: {features['len']} points")
        print(f"       Mean: {features['mean']:.4e}, Variance: {features['var']:.4e}")
        print(f"       Kurtosis: {features['kurtosis']:.4f}, Peaks: {features['n_peaks']:.0f}")
        
        # Step 4b: Detect anomaly
        print(f"\n  [4b] Running anomaly detection...")
        detection = detector.detect(features)
        
        print(f"    ✅ Detection Result:")
        print(f"       Detected: {detection['detected']}")
        print(f"       Probability: {detection['probability']:.4f} ({detection['probability']:.1%})")
        print(f"       Severity: {detection['severity']}")
        print(f"       Confidence: {detection['confidence']:.4f}")
        print(f"       Characteristics: {detection['characteristics']}")
        
        # Validation
        correct = (detection['detected'] == bool(ground_truth_anomaly))
        status = "✅ CORRECT" if correct else "❌ INCORRECT"
        print(f"\n    Validation: {status}")
        
        # Step 4c: Root cause analysis (only if anomaly detected)
        root_causes = []
        if detection['detected']:
            print(f"\n  [4c] Performing root cause analysis...")
            
            root_causes = kg.find_root_causes(
                anomalous_channels=[channel],
                anomaly_probability=detection['probability'],
                severity=detection['severity'],
                characteristics=detection['characteristics'],
                top_k=5
            )
            
            print(f"    ✅ Root Causes Identified ({len(root_causes)}):")
            for i, cause in enumerate(root_causes, 1):
                print(f"       {i}. {cause['fault_name']} ({cause['confidence']:.1%} confidence)")
                print(f"          → {cause['description']}")
                print(f"          → Affected: {', '.join(cause['affected_channels'])}")
        
        # Store results
        results.append({
            'segment_id': segment_id,
            'channel': channel,
            'ground_truth': ground_truth_anomaly,
            'detected': detection['detected'],
            'probability': detection['probability'],
            'severity': detection['severity'],
            'characteristics': detection['characteristics'],
            'root_causes': root_causes,
            'correct': correct
        })
    
    # ============ STEP 5: Summary Statistics ============
    print("\n" + "="*80)
    print("PIPELINE TEST SUMMARY")
    print("="*80)
    
    total_tests = len(results)
    correct_detections = sum(1 for r in results if r['correct'])
    accuracy = correct_detections / total_tests if total_tests > 0 else 0
    
    anomalies_found = sum(1 for r in results if r['detected'])
    avg_probability = np.mean([r['probability'] for r in results])
    
    print(f"\n  Detection Performance:")
    print(f"    Total segments tested: {total_tests}")
    print(f"    Correct detections: {correct_detections}/{total_tests} ({accuracy:.1%})")
    print(f"    Anomalies detected: {anomalies_found}")
    print(f"    Average probability: {avg_probability:.4f}")
    
    print(f"\n  Root Cause Analysis:")
    total_rca_performed = sum(1 for r in results if r['root_causes'])
    avg_causes_per_anomaly = np.mean([len(r['root_causes']) for r in results if r['root_causes']]) if total_rca_performed > 0 else 0
    print(f"    RCA performed: {total_rca_performed} times")
    print(f"    Avg causes per anomaly: {avg_causes_per_anomaly:.1f}")
    
    # Most common root causes
    all_causes = {}
    for r in results:
        for cause in r['root_causes']:
            fault_name = cause['fault_name']
            if fault_name not in all_causes:
                all_causes[fault_name] = []
            all_causes[fault_name].append(cause['confidence'])
    
    if all_causes:
        print(f"\n  Top Root Causes Identified:")
        sorted_causes = sorted(all_causes.items(), key=lambda x: np.mean(x[1]), reverse=True)
        for i, (fault_name, confidences) in enumerate(sorted_causes[:5], 1):
            avg_conf = np.mean(confidences)
            count = len(confidences)
            print(f"    {i}. {fault_name}: {avg_conf:.1%} avg confidence ({count} occurrences)")
    
    # ============ STEP 6: Detailed Results Table ============
    print("\n" + "="*80)
    print("DETAILED RESULTS")
    print("="*80)
    
    print(f"\n{'Segment':<10} {'Channel':<12} {'Truth':<8} {'Detected':<10} {'Prob':<8} {'Severity':<10} {'Status':<10} {'Top Cause':<35}")
    print("─" * 110)
    
    for r in results:
        truth_str = "ANOM" if r['ground_truth'] == 1 else "NORM"
        detected_str = "YES" if r['detected'] else "NO"
        prob_str = f"{r['probability']:.3f}"
        severity_str = r['severity']
        status_str = "✓" if r['correct'] else "✗"
        
        top_cause = ""
        if r['root_causes']:
            top_cause = r['root_causes'][0]['fault_name'][:33]
        
        print(f"{r['segment_id']:<10} {r['channel']:<12} {truth_str:<8} {detected_str:<10} {prob_str:<8} {severity_str:<10} {status_str:<10} {top_cause:<35}")
    
    print("\n" + "="*80)
    if accuracy >= 0.8:
        print("✅ PIPELINE TEST PASSED (≥80% accuracy)")
    else:
        print("⚠️  PIPELINE TEST NEEDS REVIEW (<80% accuracy)")
    print("="*80)
    
    return results


def test_single_normal_segment():
    """
    Test a single normal segment to verify false positive rate
    """
    print("\n" + "="*80)
    print("FALSE POSITIVE TEST (Normal Segment)")
    print("="*80)
    
    ingestor = TelemetryIngestor()
    segments_df = ingestor.load_segments(limit=5000)
    
    # Find a normal segment
    normal_segments = segments_df[segments_df['anomaly'] == 0]['segment'].unique()
    
    if len(normal_segments) == 0:
        print("⚠️  No normal segments found in loaded data")
        return
    
    test_segment_id = normal_segments[0]
    segment_data = segments_df[segments_df['segment'] == test_segment_id]
    
    print(f"\nTesting segment {test_segment_id} (ground truth: NORMAL)")
    print(f"  Channel: {segment_data['channel'].iloc[0]}")
    print(f"  Readings: {len(segment_data)}")
    
    # Extract features
    features = ingestor.extract_features_for_segment(segment_data)
    
    # Detect
    detector = AnomalyDetector(
        Path('dataset/anomaly_model.pt'),
        Path('dataset/anomaly_scaler.pkl')
    )
    detection = detector.detect(features)
    
    print(f"\n  Detection Result:")
    print(f"    Detected: {detection['detected']}")
    print(f"    Probability: {detection['probability']:.4f}")
    print(f"    Severity: {detection['severity']}")
    
    if not detection['detected']:
        print("\n✅ TEST PASSED: Correctly classified as NORMAL")
    else:
        print("\n⚠️  FALSE POSITIVE: Incorrectly classified as ANOMALY")
        print(f"    (This happens {detection['probability']:.1%} of the time based on threshold)")


if __name__ == '__main__':
    # Run main pipeline test
    results = test_end_to_end_pipeline()
    
    # Run false positive test
    test_single_normal_segment()
    
    print("\n" + "="*80)
    print("🎯 ALL TESTS COMPLETED")
    print("="*80)
