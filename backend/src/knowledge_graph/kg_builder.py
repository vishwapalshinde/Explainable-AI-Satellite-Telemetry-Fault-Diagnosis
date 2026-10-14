"""
Knowledge Graph Builder for ADCS Subsystem Root Cause Analysis
"""
import networkx as nx
from typing import Dict, List, Optional, Tuple, Set
import json
from pathlib import Path
from dataclasses import dataclass, asdict

from ..config import settings
from ..utils.logger import get_logger, LogContext

logger = get_logger()


@dataclass
class KGNode:
    """Knowledge Graph Node representing a system component"""
    id: str
    type: str  # 'subsystem', 'channel', 'sensor', 'fault', 'symptom'
    name: str
    description: str
    metadata: Dict = None


@dataclass
class KGRelationship:
    """Knowledge Graph Relationship"""
    source: str
    target: str
    relation_type: str  # 'affects', 'causes', 'monitors', 'depends_on'
    weight: float = 1.0
    metadata: Dict = None


class ADCSKnowledgeGraph:
    """
    Knowledge Graph for ADCS (Attitude Determination and Control System)
    Maps relationships between channels, subsystems, and faults
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, KGNode] = {}
        self.relationships: List[KGRelationship] = []
        
        logger.info("🕸️  ADCS Knowledge Graph initialized")
    
    def add_node(self, node: KGNode):
        """Add a node to the knowledge graph"""
        self.nodes[node.id] = node
        self.graph.add_node(
            node.id,
            type=node.type,
            name=node.name,
            description=node.description,
            metadata=node.metadata or {}
        )
        logger.debug(f"➕ Added node: {node.id} ({node.type})")
    
    def add_relationship(self, relationship: KGRelationship):
        """Add a relationship to the knowledge graph"""
        self.relationships.append(relationship)
        self.graph.add_edge(
            relationship.source,
            relationship.target,
            relation_type=relationship.relation_type,
            weight=relationship.weight,
            metadata=relationship.metadata or {}
        )
        logger.debug(
            f"🔗 Added relationship: {relationship.source} "
            f"-[{relationship.relation_type}]-> {relationship.target}"
        )
    
    def build_adcs_ontology(self):
        """
        Build the ADCS subsystem ontology with channels and relationships
        Based on typical satellite ADCS architecture
        """
        with LogContext("Building ADCS Knowledge Graph Ontology"):
            
            # ================================================================
            # ADCS ROOT SUBSYSTEM
            # ================================================================
            self.add_node(KGNode(
                id="adcs_subsystem",
                type="subsystem",
                name="ADCS",
                description="Attitude Determination and Control System",
                metadata={"criticality": "high", "level": 0}
            ))
            
            # ================================================================
            # MAGNETOMETER SUBSYSTEM
            # ================================================================
            self.add_node(KGNode(
                id="magnetometer_subsystem",
                type="subsystem",
                name="Magnetometer Subsystem",
                description="3-axis magnetometer for attitude determination",
                metadata={"sensor_type": "magnetometer", "axes": 3}
            ))
            
            # Magnetometer Channels (X, Y, Z axes)
            magnetometer_channels = [
                ("CADC0872", "Magnetometer X-axis", "Magnetic field X component"),
                ("CADC0873", "Magnetometer Y-axis", "Magnetic field Y component"),
                ("CADC0874", "Magnetometer Z-axis", "Magnetic field Z component"),
            ]
            
            for channel_id, name, desc in magnetometer_channels:
                self.add_node(KGNode(
                    id=channel_id,
                    type="channel",
                    name=name,
                    description=desc,
                    metadata={"unit": "Tesla", "sensor_type": "magnetometer"}
                ))
                
                # Link channel to subsystem
                self.add_relationship(KGRelationship(
                    source=channel_id,
                    target="magnetometer_subsystem",
                    relation_type="belongs_to",
                    weight=1.0
                ))
                
                self.add_relationship(KGRelationship(
                    source="magnetometer_subsystem",
                    target="adcs_subsystem",
                    relation_type="part_of",
                    weight=1.0
                ))
            
            # ================================================================
            # PHOTODIODE SUBSYSTEM (Sun Sensors)
            # ================================================================
            self.add_node(KGNode(
                id="photodiode_subsystem",
                type="subsystem",
                name="Photodiode/Sun Sensor Subsystem",
                description="6 photodiodes for sun vector determination",
                metadata={"sensor_type": "photodiode", "count": 6}
            ))
            
            # Photodiode Channels (6 sensors)
            photodiode_channels = [
                ("CADC0875", "Photodiode 1", "Sun sensor photodiode 1"),
                ("CADC0876", "Photodiode 2", "Sun sensor photodiode 2"),
                ("CADC0877", "Photodiode 3", "Sun sensor photodiode 3"),
                ("CADC0878", "Photodiode 4", "Sun sensor photodiode 4"),
                ("CADC0879", "Photodiode 5", "Sun sensor photodiode 5"),
                ("CADC0880", "Photodiode 6", "Sun sensor photodiode 6"),
            ]
            
            for channel_id, name, desc in photodiode_channels:
                self.add_node(KGNode(
                    id=channel_id,
                    type="channel",
                    name=name,
                    description=desc,
                    metadata={"unit": "Volts", "sensor_type": "photodiode"}
                ))
                
                # Link channel to subsystem
                self.add_relationship(KGRelationship(
                    source=channel_id,
                    target="photodiode_subsystem",
                    relation_type="belongs_to",
                    weight=1.0
                ))
                
                self.add_relationship(KGRelationship(
                    source="photodiode_subsystem",
                    target="adcs_subsystem",
                    relation_type="part_of",
                    weight=1.0
                ))
            
            # ================================================================
            # CROSS-CHANNEL DEPENDENCIES
            # ================================================================
            # Magnetometer axes correlation
            self.add_relationship(KGRelationship(
                source="CADC0872",
                target="CADC0873",
                relation_type="correlates_with",
                weight=0.7,
                metadata={"reason": "orthogonal_axes"}
            ))
            
            self.add_relationship(KGRelationship(
                source="CADC0873",
                target="CADC0874",
                relation_type="correlates_with",
                weight=0.7,
                metadata={"reason": "orthogonal_axes"}
            ))
            
            self.add_relationship(KGRelationship(
                source="CADC0872",
                target="CADC0874",
                relation_type="correlates_with",
                weight=0.7,
                metadata={"reason": "orthogonal_axes"}
            ))
            
            # ================================================================
            # FAULT TYPES (Comprehensive ADCS Fault Taxonomy)
            # ================================================================
            fault_types = [
                ("magnetometer_calibration_drift", "Magnetometer Calibration Drift", 
                 "Calibration parameters degraded over time", 
                 {"severity": "high", "typical_prob": 0.89, 
                  "characteristics": ["mean_shift", "high_variance"]}),
                
                ("adcs_control_instability", "ADCS Control Instability", 
                 "Feedback loop oscillation or controller instability", 
                 {"severity": "high", "typical_prob": 0.76, 
                  "characteristics": ["oscillation", "dynamics_change"]}),
                
                ("sensor_noise_interference", "Sensor Noise/Interference", 
                 "Increased noise or electromagnetic interference", 
                 {"severity": "medium", "typical_prob": 0.65, 
                  "characteristics": ["high_variance", "outliers"]}),
                
                ("reaction_wheel_momentum_dump", "Reaction Wheel Momentum Saturation", 
                 "Momentum wheels reached saturation, dump event occurred", 
                 {"severity": "critical", "typical_prob": 0.82, 
                  "characteristics": ["mean_shift", "dynamics_change"]}),
                
                ("magnetic_disturbance", "Magnetic Field Disturbance", 
                 "Solar activity or geomagnetic storm affecting measurements", 
                 {"severity": "medium", "typical_prob": 0.58, 
                  "characteristics": ["mean_shift", "oscillation"]}),
                
                ("attitude_determination_error", "Attitude Determination Error", 
                 "Errors in attitude estimation algorithm", 
                 {"severity": "high", "typical_prob": 0.71, 
                  "characteristics": ["mean_shift", "outliers"]}),
                
                ("thermal_anomaly", "Thermal Condition Anomaly", 
                 "Temperature extremes affecting sensor performance", 
                 {"severity": "medium", "typical_prob": 0.68, 
                  "characteristics": ["mean_shift", "high_variance"]}),
                
                ("power_supply_fluctuation", "Power Supply Fluctuation", 
                 "Voltage instability affecting sensor power", 
                 {"severity": "high", "typical_prob": 0.73, 
                  "characteristics": ["high_variance", "outliers"]}),
                
                ("sensor_bias", "Sensor Bias/Offset", 
                 "Constant offset in sensor readings", 
                 {"severity": "medium", "typical_prob": 0.62, 
                  "characteristics": ["mean_shift"]}),
                
                ("communication_link_degradation", "Communication Link Degradation", 
                 "Data transmission errors or packet loss", 
                 {"severity": "critical", "typical_prob": 0.75, 
                  "characteristics": ["outliers", "high_variance"]})
            ]
            
            for fault_id, name, desc, metadata in fault_types:
                self.add_node(KGNode(
                    id=fault_id,
                    type="fault",
                    name=name,
                    description=desc,
                    metadata=metadata
                ))
            
            # ================================================================
            # FAULT-TO-CHANNEL MAPPINGS (Causal Relationships)
            # ================================================================
            
            # Magnetometer-specific faults
            magnetometer_channels = ["CADC0872", "CADC0873", "CADC0874"]
            
            for channel_id in magnetometer_channels:
                # Magnetometer calibration drift affects all mag axes
                self.add_relationship(KGRelationship(
                    source="magnetometer_calibration_drift",
                    target=channel_id,
                    relation_type="can_cause_anomaly_in",
                    weight=0.92
                ))
                
                # Magnetic disturbances affect magnetometers  
                self.add_relationship(KGRelationship(
                    source="magnetic_disturbance",
                    target=channel_id,
                    relation_type="can_cause_anomaly_in",
                    weight=0.88
                ))
                
                # Thermal anomalies particularly affect magnetometers
                self.add_relationship(KGRelationship(
                    source="thermal_anomaly",
                    target=channel_id,
                    relation_type="can_cause_anomaly_in",
                    weight=0.75
                ))
            
            # Photodiode-specific faults
            photodiode_channels = ["CADC0875", "CADC0876", "CADC0877", "CADC0878", "CADC0879", "CADC0880"]
            
            for channel_id in photodiode_channels:
                # Power supply fluctuation affects photodiodes more
                self.add_relationship(KGRelationship(
                    source="power_supply_fluctuation",
                    target=channel_id,
                    relation_type="can_cause_anomaly_in",
                    weight=0.87
                ))
                
                # Sensor bias can affect sun sensors
                self.add_relationship(KGRelationship(
                    source="sensor_bias",
                    target=channel_id,
                    relation_type="can_cause_anomaly_in",
                    weight=0.70
                ))
            
            # System-wide faults affecting all sensors
            all_channels = magnetometer_channels + photodiode_channels
            
            for channel_id in all_channels:
                # ADCS control instability affects all sensors
                self.add_relationship(KGRelationship(
                    source="adcs_control_instability",
                    target=channel_id,
                    relation_type="can_cause_anomaly_in",
                    weight=0.78
                ))
                
                # Communication link issues can affect any channel
                self.add_relationship(KGRelationship(
                    source="communication_link_degradation",
                    target=channel_id,
                    relation_type="can_cause_anomaly_in",
                    weight=0.65
                ))
                
                # Noise/interference can affect any sensor
                self.add_relationship(KGRelationship(
                    source="sensor_noise_interference",
                    target=channel_id,
                    relation_type="can_cause_anomaly_in",
                    weight=0.68
                ))
            
            # Reaction wheel momentum dump affects primarily magnetometers (due to disturbance torques)
            for channel_id in magnetometer_channels:
                self.add_relationship(KGRelationship(
                    source="reaction_wheel_momentum_dump",
                    target=channel_id,
                    relation_type="can_cause_anomaly_in",
                    weight=0.85
                ))
            
            # Attitude determination errors propagate to all ADCS sensors
            for channel_id in all_channels:
                self.add_relationship(KGRelationship(
                    source="attitude_determination_error",
                    target=channel_id,
                    relation_type="can_cause_anomaly_in",
                    weight=0.72
                ))
            
            logger.info(f"✅ ADCS ontology built:")
            logger.info(f"   Nodes: {self.graph.number_of_nodes()}")
            logger.info(f"   Relationships: {self.graph.number_of_edges()}")
    
    def find_root_causes(
        self, 
        anomalous_channels: List[str], 
        anomaly_probability: float = 0.5,
        severity: str = 'MEDIUM',
        characteristics: List[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find probable root causes for anomalies with advanced confidence scoring
        
        Args:
            anomalous_channels: List of channel IDs showing anomalies
            anomaly_probability: ML model's anomaly probability (0.0-1.0)
            severity: Anomaly severity (LOW/MEDIUM/HIGH/CRITICAL)
            characteristics: Detected characteristics (high_variance, mean_shift, etc.)
            top_k: Number of top root causes to return
            
        Returns:
            List of dicts with fault_id, fault_name, confidence, explanation
        """
        with LogContext("Finding root causes with advanced scoring"):
            fault_scores = {}
            fault_explanations = {}
            characteristics = characteristics or []
            
            # Find all fault nodes that can affect the anomalous channels
            for channel_id in anomalous_channels:
                if channel_id not in self.graph:
                    logger.warning(f"⚠️  Channel {channel_id} not in knowledge graph")
                    continue
                
                # Find predecessors (potential causes)
                for fault_node in self.graph.predecessors(channel_id):
                    node_data = self.graph.nodes[fault_node]
                    if node_data.get('type') == 'fault':
                        edge_data = self.graph.get_edge_data(fault_node, channel_id)
                        edge_weight = edge_data.get('weight', 1.0)
                        
                        # Base score from graph structure
                        if fault_node not in fault_scores:
                            fault_scores[fault_node] = 0.0
                            fault_explanations[fault_node] = []
                        
                        fault_scores[fault_node] += edge_weight
                        
                        # Track which channels are affected
                        channel_name = self.nodes[channel_id].name if channel_id in self.nodes else channel_id
                        fault_explanations[fault_node].append(channel_name)
            
            # Calculate confidence scores with multiple factors
            confidence_scores = {}
            
            for fault_id, base_score in fault_scores.items():
                fault_node = self.nodes.get(fault_id)
                if not fault_node:
                    continue
                
                # Factor 1: Graph structure score (normalized)
                max_base_score = max(fault_scores.values()) if fault_scores else 1.0
                structure_score = base_score / max_base_score
                
                # Factor 2: Severity alignment
                fault_severity = fault_node.metadata.get('severity', 'medium')
                severity_map = {
                    'CRITICAL': {'critical': 1.0, 'high': 0.85, 'medium': 0.6, 'low': 0.3},
                    'HIGH': {'critical': 0.85, 'high': 1.0, 'medium': 0.75, 'low': 0.4},
                    'MEDIUM': {'critical': 0.6, 'high': 0.75, 'medium': 1.0, 'low': 0.6},
                    'LOW': {'critical': 0.3, 'high': 0.4, 'medium': 0.6, 'low': 1.0}
                }
                severity_factor = severity_map.get(severity, {}).get(fault_severity, 0.5)
                
                # Factor 3: Characteristic match
                fault_characteristics = fault_node.metadata.get('characteristics', [])
                if characteristics and fault_characteristics:
                    matching = set(characteristics) & set(fault_characteristics)
                    char_match_factor = len(matching) / len(fault_characteristics) if fault_characteristics else 0.5
                else:
                    char_match_factor = 0.7  # Neutral if no characteristics
                
                # Factor 4: Anomaly probability boost
                prob_factor = 0.5 + (anomaly_probability * 0.5)  # Scale 0.5-1.0
                
                # Combine factors (weighted average)
                confidence = (
                    structure_score * 0.35 +      # 35% graph structure
                    severity_factor * 0.25 +       # 25% severity match
                    char_match_factor * 0.20 +     # 20% characteristic match
                    prob_factor * 0.20             # 20% ML confidence
                )
                
                confidence_scores[fault_id] = min(confidence, 1.0)
            
            # Sort by confidence and prepare results
            ranked_faults = sorted(
                confidence_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_k]
            
            # Format results
            results = []
            for fault_id, confidence in ranked_faults:
                fault_node = self.nodes[fault_id]
                affected_channels = fault_explanations.get(fault_id, [])
                
                results.append({
                    'fault_id': fault_id,
                    'fault_name': fault_node.name,
                    'confidence': float(confidence),
                    'description': fault_node.description,
                    'affected_channels': affected_channels,
                    'severity': fault_node.metadata.get('severity', 'unknown')
                })
            
            logger.info(f"✅ Found {len(results)} probable root causes:")
            for result in results:
                logger.info(f"   {result['fault_name']}: {result['confidence']:.1%}")
            
            return results
    
    def get_affected_subsystems(self, anomalous_channels: List[str]) -> Set[str]:
        """Get subsystems affected by anomalous channels"""
        affected_subsystems = set()
        
        for channel_id in anomalous_channels:
            if channel_id not in self.graph:
                continue
            
            # Traverse to find parent subsystems
            for successor in self.graph.successors(channel_id):
                if self.graph.nodes[successor].get('type') == 'subsystem':
                    affected_subsystems.add(successor)
        
        return affected_subsystems
    
    def export_to_json(self, filepath: Path):
        """Export knowledge graph to JSON"""
        export_data = {
            'nodes': [asdict(node) for node in self.nodes.values()],
            'relationships': [asdict(rel) for rel in self.relationships]
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"💾 Knowledge graph exported: {filepath}")
    
    def visualize(self, save_path: Optional[Path] = None):
        """Visualize the knowledge graph"""
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(16, 12))
            
            # Node colors by type
            color_map = {
                'subsystem': '#FF6B6B',
                'channel': '#4ECDC4',
                'fault': '#FFD93D',
                'sensor': '#95E1D3'
            }
            
            node_colors = [
                color_map.get(self.graph.nodes[node].get('type', 'sensor'), '#CCCCCC')
                for node in self.graph.nodes()
            ]
            
            # Layout
            pos = nx.spring_layout(self.graph, k=2, iterations=50)
            
            # Draw
            nx.draw(
                self.graph,
                pos,
                node_color=node_colors,
                node_size=1000,
                font_size=8,
                font_weight='bold',
                with_labels=True,
                edge_color='gray',
                arrows=True,
                arrowsize=15
            )
            
            plt.title("ADCS Knowledge Graph", fontsize=16, fontweight='bold')
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"💾 Knowledge graph visualization saved: {save_path}")
            
            plt.close()
            
        except ImportError:
            logger.warning("⚠️  matplotlib not available for visualization")
