"""
Fault Diagnosis Engine - Integration Layer for Complete Diagnosis Pipeline
Combines: Feature Extraction → Anomaly Detection → Root Cause Analysis → LLM Explanation
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json

from ..models.anomaly_detector import AnomalyDetector, CharacteristicsExtractor
from ..knowledge_graph.kg_builder import ADCSKnowledgeGraph
from .diagnosis_explainer import DiagnosisExplainer, create_knowledge_base_documents
from ..processing.feature_extractor import SegmentFeatureExtractor
from ..utils.logger import get_logger, LogContext

logger = get_logger()


class FaultDiagnosisEngine:
    """
    Complete fault diagnosis engine integrating all analysis layers
    
    Pipeline:
    1. Feature Extraction (from raw telemetry)
    2. Anomaly Detection (FCNN neural network)
    3. Root Cause Analysis (Knowledge Graph reasoning)
    4. Interactive Diagnosis (LLM + RAG explanation)
    """
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        scaler_path: Optional[Path] = None,
        vector_store_path: Optional[Path] = None,
        initialize_rag: bool = True
    ):
        """
        Initialize the complete diagnosis engine
        
        Args:
            model_path: Path to trained FCNN model
            scaler_path: Path to feature scaler
            vector_store_path: Path to RAG vector store
            initialize_rag: Whether to initialize RAG components (set False if Ollama not available)
        """
        logger.info("🚀 Initializing Fault Diagnosis Engine...")
        
        # Module 1: Feature Extraction
        self.feature_extractor = SegmentFeatureExtractor()
        logger.info("✅ Feature Extractor loaded")
        
        # Module 2: Anomaly Detection
        self.anomaly_detector = AnomalyDetector(
            model_path=model_path,
            scaler_path=scaler_path
        )
        self.char_extractor = CharacteristicsExtractor()
        logger.info("✅ Anomaly Detector loaded")
        
        # Module 3: Knowledge Graph
        self.kg = ADCSKnowledgeGraph()
        self.kg.build_adcs_ontology()
        logger.info("✅ Knowledge Graph built")
        
        # Module 4: LLM Explainer (optional)
        self.llm_explainer = None
        self.rag_initialized = False
        
        if initialize_rag:
            try:
                self.llm_explainer = DiagnosisExplainer(vector_store_path=vector_store_path)
                
                # Load knowledge base
                kb_docs = create_knowledge_base_documents()
                self.llm_explainer.load_knowledge_base(kb_docs)
                self.llm_explainer.initialize_qa_chain()
                
                self.rag_initialized = True
                logger.info("✅ LLM + RAG initialized")
            except Exception as e:
                logger.warning(f"⚠️ RAG initialization failed (Ollama may not be running): {e}")
                logger.info("💡 Operating without LLM - using rule-based explanations")
        
        # Inference history for context-aware diagnosis
        self.inference_history: List[Dict] = []
        
        logger.info("🎯 Fault Diagnosis Engine ready!")
    
    def diagnose_segment(
        self,
        values: List[float],
        timestamps: List[float],
        segment_id: str,
        channel: str,
        use_llm: bool = True
    ) -> Dict:
        """
        Complete end-to-end diagnosis for a telemetry segment
        
        Args:
            values: Raw telemetry values
            timestamps: Corresponding timestamps
            segment_id: Unique segment identifier
            channel: Channel ID (e.g., 'CADC0872')
            use_llm: Whether to use LLM for explanation (requires RAG)
            
        Returns:
            Complete diagnosis dictionary with detection, RCA, and explanation
        """
        with LogContext(f"Diagnosing segment {segment_id} ({channel})"):
            
            # Step 1: Extract features
            features = self.feature_extractor.extract_features_from_segment(
                values=values,
                timestamps=timestamps,
                segment_id=segment_id,
                channel=channel
            )
            logger.info(f"📊 Extracted {len(features)} features")
            
            # Step 2: Detect anomaly
            detection_result = self.anomaly_detector.detect(features)
            
            is_anomaly = detection_result['detected']
            probability = detection_result['probability']
            severity = detection_result['severity']
            
            logger.info(
                f"🔍 Detection: {'ANOMALY' if is_anomaly else 'NORMAL'} "
                f"(P={probability:.3f}, Severity={severity})"
            )
            
            # Step 3: Root Cause Analysis (if anomaly detected)
            root_causes = []
            if is_anomaly:
                # Extract characteristics for KG
                characteristics = self.char_extractor.extract_characteristics(features)
                
                # Query knowledge graph
                root_causes = self.kg.find_root_causes(
                    anomalous_channels=[channel],
                    anomaly_probability=probability,
                    severity=severity,
                    characteristics=characteristics,
                    top_k=5
                )
                
                logger.info(f"🎯 Identified {len(root_causes)} root causes")
                if root_causes:
                    top_cause = root_causes[0]
                    logger.info(
                        f"   Top cause: {top_cause['fault_name']} "
                        f"({top_cause['confidence']*100:.1f}% confidence)"
                    )
            
            # Step 4: Generate explanation
            explanation = None
            if is_anomaly and use_llm and self.rag_initialized:
                try:
                    explanation = self._generate_llm_explanation(
                        features=features,
                        detection_result=detection_result,
                        root_causes=root_causes,
                        channel=channel
                    )
                    logger.info("💬 LLM explanation generated")
                except Exception as e:
                    logger.warning(f"LLM explanation failed: {e}")
                    explanation = self._generate_rule_based_explanation(
                        detection_result, root_causes, channel
                    )
            elif is_anomaly:
                explanation = self._generate_rule_based_explanation(
                    detection_result, root_causes, channel
                )
            
            # Build complete diagnosis
            diagnosis = {
                'segment_id': segment_id,
                'channel': channel,
                'timestamp': datetime.now().isoformat(),
                
                # Features
                'features': features,
                
                # Detection
                'detection': {
                    'is_anomaly': is_anomaly,
                    'probability': float(probability),
                    'severity': severity,
                    'confidence': float(detection_result['confidence']),
                    'characteristics': detection_result['characteristics']
                },
                
                # Root Cause Analysis
                'root_causes': root_causes,
                
                # Explanation
                'explanation': explanation,
                
                # Metadata
                'method': 'llm' if (explanation and use_llm and self.rag_initialized) else 'rule_based',
                'inference_history_size': len(self.inference_history)
            }
            
            # Store in history
            self.inference_history.append({
                'timestamp': datetime.now(),
                'segment_id': segment_id,
                'channel': channel,
                'is_anomaly': is_anomaly,
                'probability': probability,
                'top_cause': root_causes[0]['fault_name'] if root_causes else None
            })
            
            # Keep only last 100 inferences
            if len(self.inference_history) > 100:
                self.inference_history = self.inference_history[-100:]
            
            return diagnosis
    
    def _generate_llm_explanation(
        self,
        features: Dict,
        detection_result: Dict,
        root_causes: List[Dict],
        channel: str
    ) -> Dict:
        """Generate LLM-powered explanation using RAG"""
        
        # Build anomaly summary for explainer
        anomaly_summary = {
            'probability': detection_result['probability'],
            'severity': detection_result['severity'],
            'characteristics': detection_result['characteristics'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Convert root causes to tuple format expected by explainer
        rc_tuples = [
            (rc['fault_id'], rc['confidence'])
            for rc in root_causes
        ]
        
        # Generate explanation
        explanation = self.llm_explainer.generate_explanation(
            anomaly_summary=anomaly_summary,
            root_causes=rc_tuples,
            affected_channels=[channel]
        )
        
        return explanation
    
    def _generate_rule_based_explanation(
        self,
        detection_result: Dict,
        root_causes: List[Dict],
        channel: str
    ) -> Dict:
        """Generate rule-based explanation (fallback when LLM unavailable)"""
        
        severity = detection_result['severity']
        probability = detection_result['probability']
        characteristics = detection_result['characteristics']
        
        # Build explanation text
        explanation_parts = [
            f"Anomaly detected in {channel} with {probability*100:.1f}% probability.",
            f"Severity level: {severity}.",
            ""
        ]
        
        if characteristics:
            explanation_parts.append(
                f"Observable characteristics: {', '.join(characteristics)}."
            )
            explanation_parts.append("")
        
        if root_causes:
            explanation_parts.append("Probable root causes:")
            for i, rc in enumerate(root_causes[:3], 1):
                explanation_parts.append(
                    f"{i}. {rc['fault_name']} ({rc['confidence']*100:.1f}% confidence)"
                )
                if rc.get('description'):
                    explanation_parts.append(f"   → {rc['description']}")
            explanation_parts.append("")
        
        # Corrective actions
        corrective_actions = self._get_corrective_actions(root_causes, severity)
        
        explanation_text = "\n".join(explanation_parts)
        
        return {
            'explanation': explanation_text,
            'corrective_actions': corrective_actions,
            'severity': severity,
            'confidence': root_causes[0]['confidence'] if root_causes else probability,
            'source_references': ['Rule-based system']
        }
    
    def _get_corrective_actions(
        self,
        root_causes: List[Dict],
        severity: str
    ) -> List[str]:
        """Get corrective actions based on root causes"""
        
        actions = []
        
        # Fault-specific actions
        action_map = {
            'magnetometer_calibration_drift': [
                "Perform magnetometer recalibration using Earth's magnetic field model",
                "Update bias compensation parameters in flight software",
                "Schedule increased calibration frequency"
            ],
            'adcs_control_instability': [
                "Review controller gain parameters",
                "Check for actuator saturation or momentum buildup",
                "Consider adjusting control law or switching to safe mode"
            ],
            'sensor_noise_interference': [
                "Investigate electromagnetic interference sources",
                "Review power supply stability",
                "Apply additional software filtering if needed"
            ],
            'reaction_wheel_momentum_dump': [
                "Execute planned momentum dump maneuver",
                "Verify magnetic torquer operation",
                "Monitor momentum accumulation rate"
            ],
            'magnetic_disturbance': [
                "Check for geomagnetic storm activity (space weather)",
                "Verify no onboard magnetic field sources activated",
                "Consider attitude adjustment for reduced magnetic interaction"
            ],
            'attitude_determination_error': [
                "Cross-check with star tracker and gyroscope data",
                "Verify sensor alignment and calibration",
                "Review attitude determination filter health"
            ],
            'thermal_anomaly': [
                "Check thermal control system status",
                "Review sensor operating temperature range",
                "Adjust spacecraft attitude for thermal stability"
            ],
            'power_supply_fluctuation': [
                "Monitor power bus voltage and current",
                "Check for power system anomalies",
                "Consider switching to redundant power channel"
            ],
            'sensor_bias': [
                "Recalibrate affected sensor",
                "Update bias compensation parameters",
                "Monitor bias stability over orbital cycles"
            ],
            'communication_link_degradation': [
                "Verify telemetry quality metrics",
                "Check for data packet loss or corruption",
                "Request telemetry retransmission if needed"
            ]
        }
        
        # Add actions for top 2 root causes
        for rc in root_causes[:2]:
            fault_id = rc['fault_id']
            if fault_id in action_map:
                actions.extend(action_map[fault_id])
        
        # Severity-based actions
        if severity == 'CRITICAL':
            actions.insert(0, "🚨 CRITICAL: Notify Mission Control immediately")
            actions.insert(1, "Assess impact on spacecraft safety")
        elif severity == 'HIGH':
            actions.insert(0, "⚠️ HIGH: Increase telemetry monitoring frequency")
        
        # Generic monitoring action
        actions.append("Continue monitoring telemetry for pattern changes")
        actions.append("Log event in spacecraft operations timeline")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_actions = []
        for action in actions:
            if action not in seen:
                seen.add(action)
                unique_actions.append(action)
        
        return unique_actions
    
    def chat_diagnosis(
        self,
        message: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Interactive chat for diagnosis explanation
        
        Args:
            message: User's question
            context: Current diagnosis context (detection, root causes, etc.)
            
        Returns:
            Chat response with explanation and suggested actions
        """
        
        if not self.rag_initialized:
            return {
                'response': (
                    "LLM chat is currently unavailable. "
                    "Operating in rule-based mode. "
                    "Please refer to the diagnosis results for detailed information."
                ),
                'actions': [],
                'confidence': 0.0
            }
        
        try:
            # Build RAG query with context
            if context:
                query = self._build_chat_query(message, context)
            else:
                query = message
            
            # Query RAG chain
            response = self.llm_explainer.qa_chain.invoke(query)
            
            # Extract actionable items
            actions = self._extract_actions_from_text(response)
            
            return {
                'response': response,
                'actions': actions,
                'confidence': 0.85,  # Placeholder - could be computed from retrieval scores
                'method': 'rag'
            }
            
        except Exception as e:
            logger.error(f"Chat diagnosis failed: {e}")
            return {
                'response': f"Unable to generate response: {str(e)}",
                'actions': [],
                'confidence': 0.0
            }
    
    def _build_chat_query(self, message: str, context: Dict) -> str:
        """Build contextualized query for RAG"""
        
        detection = context.get('detection', {})
        root_causes = context.get('root_causes', [])
        channel = context.get('channel', 'Unknown')
        
        query = f"""
Current Diagnosis Context:
- Channel: {channel}
- Anomaly Probability: {detection.get('probability', 0)*100:.1f}%
- Severity: {detection.get('severity', 'Unknown')}
- Characteristics: {', '.join(detection.get('characteristics', []))}

Top Root Causes:
"""
        for i, rc in enumerate(root_causes[:3], 1):
            query += f"\n{i}. {rc.get('fault_name', 'Unknown')} ({rc.get('confidence', 0)*100:.1f}%)"
        
        query += f"\n\nEngineer Question: {message}\n\nProvide expert guidance:"
        
        return query
    
    def _extract_actions_from_text(self, text: str) -> List[str]:
        """Extract actionable items from LLM response"""
        
        actions = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for numbered lists or bullet points
            if (line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')) or
                'recommend' in line.lower() or
                'should' in line.lower() or
                'action' in line.lower()):
                # Clean up formatting
                action = line.lstrip('1234567890.-•').strip()
                if len(action) > 10:  # Meaningful action
                    actions.append(action)
        
        return actions[:5]  # Limit to 5 actions
    
    def get_inference_history(self, limit: int = 10) -> List[Dict]:
        """Get recent inference history"""
        return self.inference_history[-limit:]
    
    def get_system_status(self) -> Dict:
        """Get diagnosis engine status"""
        return {
            'feature_extractor': 'operational',
            'anomaly_detector': 'operational',
            'knowledge_graph': {
                'status': 'operational',
                'nodes': self.kg.graph.number_of_nodes(),
                'edges': self.kg.graph.number_of_edges()
            },
            'llm_explainer': 'operational' if self.rag_initialized else 'unavailable',
            'inference_count': len(self.inference_history)
        }
    
    def export_diagnosis_report(self, diagnosis: Dict, output_path: Path):
        """Export diagnosis to JSON report"""
        with open(output_path, 'w') as f:
            json.dump(diagnosis, f, indent=2)
        logger.info(f"📄 Diagnosis report exported to {output_path}")
