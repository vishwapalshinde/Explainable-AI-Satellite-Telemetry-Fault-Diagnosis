"""
LLM + RAG Explanation Layer for Fault Diagnosis
Using LangChain with local LLM (Ollama) and vector store (ChromaDB)
"""
from typing import List, Dict, Optional, Tuple, Union
from pathlib import Path
import json
import hashlib
import math
import re
import shutil
import urllib.error
import urllib.request
from datetime import datetime
from collections import Counter

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover - compatibility with older LangChain installs
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from ..config import settings
from ..utils.logger import get_logger, LogContext

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency
    PdfReader = None

logger = get_logger()


RootCause = Union[Tuple[str, float], Dict]


class _LocalHashEmbeddings:
    """Deterministic embedding fallback for offline or constrained environments."""

    def __init__(self, dimension: int = 256):
        self.dimension = dimension

    def _encode(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())

        for token in tokens:
            digest = hashlib.md5(token.encode('utf-8')).hexdigest()
            value = int(digest, 16)
            index = value % self.dimension
            sign = -1.0 if ((value >> 1) & 1) else 1.0
            vector[index] += sign

        norm = math.sqrt(sum(component * component for component in vector))
        if norm > 0:
            vector = [component / norm for component in vector]
        return vector

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._encode(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._encode(text)


class DiagnosisExplainer:
    """
    Production-grade explainable AI system for fault diagnosis
    Combines anomaly detection results, knowledge graph reasoning, and LLM explanations
    """
    
    def __init__(
        self,
        knowledge_base_path: Optional[Path] = None,
        vector_store_path: Optional[Path] = None
    ):
        """
        Initialize the explainer with RAG components
        
        Args:
            knowledge_base_path: Path to knowledge base documents
            vector_store_path: Path to persist vector store
        """
        self.knowledge_base_path = knowledge_base_path
        self.vector_store_path = vector_store_path or (settings.BASE_DIR / "vector_store" / "runtime_chroma")
        self.kb_manifest_path = self.vector_store_path / "kb_manifest.json"
        self.explanation_mode = 'deterministic_fallback'
        self.ollama_available = False
        self.ollama_error = None
        
        # Initialize embeddings
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=settings.RAG_EMBEDDING_MODEL,
                model_kwargs={'device': 'cpu'}
            )
            self.embedding_mode = 'sentence_transformers'
        except Exception as exc:
            self.embeddings = _LocalHashEmbeddings()
            self.embedding_mode = 'local_hash'
            logger.warning(f"Embedding model unavailable, using local hash embeddings: {exc}")
        
        # Initialize LLM only when the Ollama API is reachable.
        self.llm = None
        if self._check_ollama_api():
            try:
                self.llm = Ollama(
                    model=settings.LLM_MODEL,
                    base_url=settings.LLM_API_BASE,
                    temperature=settings.LLM_TEMPERATURE
                )
                self.ollama_available = True
                self.explanation_mode = 'ollama_ready'
            except Exception as exc:
                self.ollama_error = str(exc)
                logger.warning(f"Ollama client initialization failed: {exc}")
        else:
            logger.warning(
                f"Ollama API not reachable at {settings.LLM_API_BASE}; using deterministic fallback until it becomes available."
            )
        
        # Vector store and retrieval chain
        self.vector_store = None
        self.retriever = None
        self.qa_chain = None
        
        logger.info("🤖 DiagnosisExplainer initialized")
        logger.info(f"   LLM: {settings.LLM_MODEL}")
        logger.info(f"   Embedding: {settings.RAG_EMBEDDING_MODEL}")
        logger.info(f"   Embedding mode: {self.embedding_mode}")
        logger.info(f"   Ollama available: {self.ollama_available}")

    def _ensure_llm_ready(self) -> bool:
        """Best-effort runtime LLM availability refresh."""
        if self.llm is not None and self.ollama_available:
            return True

        if not self._check_ollama_api():
            self.ollama_available = False
            return False

        try:
            self.llm = Ollama(
                model=settings.LLM_MODEL,
                base_url=settings.LLM_API_BASE,
                temperature=settings.LLM_TEMPERATURE
            )
            self.ollama_available = True
            self.ollama_error = None
            if self.vector_store is not None and self.qa_chain is None:
                self.initialize_qa_chain()
            return True
        except Exception as exc:
            self.ollama_available = False
            self.ollama_error = str(exc)
            logger.warning(f"Unable to reinitialize Ollama client: {exc}")
            return False
    
    def load_knowledge_base(self, documents: List[Dict[str, str]]):
        """
        Load knowledge base documents into vector store
        
        Args:
            documents: List of dicts with 'content' and 'metadata' keys
        """
        with LogContext("Loading knowledge base into vector store"):
            kb_hash = self._kb_fingerprint(documents)
            if self._load_cached_vector_store(kb_hash):
                self.retriever = self.vector_store.as_retriever(
                    search_kwargs={"k": settings.RAG_TOP_K_RESULTS}
                )
                logger.info("✅ Knowledge base loaded from cache")
                return

            # Convert to LangChain documents
            docs = [
                Document(
                    page_content=doc['content'],
                    metadata=doc.get('metadata', {})
                )
                for doc in documents
            ]
            self.knowledge_base_documents = docs
            
            # Split documents
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.RAG_CHUNK_SIZE,
                chunk_overlap=settings.RAG_CHUNK_OVERLAP
            )
            split_docs = text_splitter.split_documents(docs)
            
            logger.info(f"📄 Split {len(docs)} documents into {len(split_docs)} chunks")
            
            # Create vector store
            try:
                self.vector_store = Chroma.from_documents(
                    documents=split_docs,
                    embedding=self.embeddings,
                    persist_directory=str(self.vector_store_path)
                )
            except Exception as exc:
                # Recover from old/incompatible on-disk schema by rebuilding store.
                error_text = str(exc).lower()
                if "no such column" in error_text or "schema" in error_text:
                    logger.warning(f"Vector store schema mismatch detected ({exc}). Rebuilding Chroma store...")
                    shutil.rmtree(self.vector_store_path, ignore_errors=True)
                    self.vector_store_path.mkdir(parents=True, exist_ok=True)
                    self.vector_store = Chroma.from_documents(
                        documents=split_docs,
                        embedding=self.embeddings,
                        persist_directory=str(self.vector_store_path)
                    )
                else:
                    raise
            
            logger.info(f"✅ Vector store created with {len(split_docs)} chunks")
            self._save_kb_manifest(kb_hash, len(split_docs))
    
    def initialize_qa_chain(self):
        """Initialize the RAG question-answering chain using LCEL"""
        if self.vector_store is None:
            raise ValueError("Vector store not initialized. Call load_knowledge_base first.")
        if self.llm is None:
            logger.warning("Ollama is not available; RAG chain will remain disabled and deterministic fallback will be used.")
            self.qa_chain = None
            return
        
        # Create prompt template for satellite fault diagnosis
        prompt_template = """You are an expert Satellite Operations Engineer specializing in ADCS (Attitude Determination and Control System) fault diagnosis.

Context from knowledge base:
{context}

Based on the context above and your expertise, answer the following question about the satellite telemetry anomaly:

Question: {question}

Provide a clear, technically accurate explanation that includes:
1. Root cause identification
2. Technical reasoning
3. Recommended corrective actions
4. Severity assessment

Answer:"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create retriever
        self.retriever = self.vector_store.as_retriever(
            search_kwargs={"k": settings.RAG_TOP_K_RESULTS}
        )
        
        # Create RAG chain using LCEL (LangChain Expression Language)
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        self.qa_chain = (
            {
                "context": self.retriever | format_docs,
                "question": RunnablePassthrough()
            }
            | PROMPT
            | self.llm
            | StrOutputParser()
        )
        
        logger.info("✅ RAG QA chain initialized")

    def _check_ollama_api(self) -> bool:
        """Check whether the Ollama HTTP API is reachable."""
        try:
            base_url = settings.LLM_API_BASE.rstrip('/')
            probe_url = f"{base_url}/api/tags"
            with urllib.request.urlopen(probe_url, timeout=2) as response:
                return 200 <= response.status < 300
        except (urllib.error.URLError, TimeoutError, ValueError):
            return False

    def _retrieve_evidence_documents(self, query: str) -> List[Document]:
        """Retrieve supporting evidence chunks for a diagnosis or chat query."""
        if self.retriever is None:
            return []

        try:
            documents = self.retriever.get_relevant_documents(query)

            priority_sources = {
                'docs/01_ADCS_Operations_Manual.pdf': 0,
                'docs/02_ADCS_Anomaly_Catalogue.pdf': 1,
                'docs/03_FDIR_Procedures_Manual.pdf': 2,
                'docs/04_Root_Cause_Analysis_Framework.pdf': 3,
                'docs/05_Corrective_Actions_Quick_Reference.pdf': 4,
                'docs/06_Feature_Engineering_Signal_Interpretation.pdf': 5,
                'docs/07_Space_Environment_Effects.pdf': 6,
            }

            def rank_document(doc: Document):
                source = str(doc.metadata.get('source', ''))
                topic = str(doc.metadata.get('topic', ''))
                section = str(doc.metadata.get('section', ''))
                base_name = source.replace('\\', '/')
                priority = priority_sources.get(base_name, 20)
                if topic in {'adcs_operations_manual', 'anomaly_catalogue', 'fdir_procedures_manual', 'root_cause_analysis_framework', 'corrective_actions_quick_reference', 'feature_engineering_guide', 'space_environment_effects'}:
                    priority = min(priority, 10)
                return (priority, source, topic, section)

            return sorted(documents, key=rank_document)
        except Exception as exc:
            logger.warning(f"Retrieval failed: {exc}")
            return []

    def _format_source_references(self, documents: List[Document]) -> List[str]:
        """Extract stable source labels from retrieved documents."""
        references: List[str] = []
        for doc in documents:
            source = doc.metadata.get('source', 'Unknown')
            section = doc.metadata.get('section')
            topic = doc.metadata.get('topic')
            if section:
                references.append(f"{source}#{section}")
            elif topic:
                references.append(f"{source}:{topic}")
            else:
                references.append(str(source))
        return list(dict.fromkeys(references))

    def _section_metadata_for_source(self, source_path: str) -> Dict[str, str]:
        """Attach section-level labels for the seven core ADCS PDFs."""
        source_name = source_path.replace('\\', '/').split('/')[-1].lower()

        section_map = {
            '01_adcs_operations_manual.pdf': ('adcs_operations_manual', 'architecture_and_nominal_modes'),
            '02_adcs_anomaly_catalogue.pdf': ('anomaly_catalogue', 'anomaly_signatures_and_symptoms'),
            '03_fdir_procedures_manual.pdf': ('fdir_procedures_manual', 'diagnosis_escalation_and_recovery'),
            '04_root_cause_analysis_framework.pdf': ('root_cause_analysis_framework', 'causal_mapping_and_scoring'),
            '05_corrective_actions_quick_reference.pdf': ('corrective_actions_quick_reference', 'action_sequences_and_decision_trees'),
            '06_feature_engineering_signal_interpretation.pdf': ('feature_engineering_guide', 'feature_patterns_and_physical_meaning'),
            '07_space_environment_effects.pdf': ('space_environment_effects', 'environmental_drivers_and_sensor_effects'),
        }

        topic, section = section_map.get(source_name, (source_name.rsplit('.', 1)[0], 'general'))
        return {
            'topic': topic,
            'section': section,
        }

    def _kb_fingerprint(self, documents: List[Dict[str, str]]) -> str:
        """Build a stable fingerprint for the KB payload."""
        normalized = []
        for doc in documents:
            content = doc.get('content', '') if isinstance(doc, dict) else ''
            metadata = doc.get('metadata', {}) if isinstance(doc, dict) else {}
            normalized.append({
                'source': metadata.get('source', ''),
                'topic': metadata.get('topic', ''),
                'content_hash': hashlib.sha256(content.encode('utf-8')).hexdigest(),
            })

        payload = json.dumps(
            sorted(normalized, key=lambda item: (item['source'], item['topic'], item['content_hash'])),
            sort_keys=True
        )
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def _load_cached_vector_store(self, kb_hash: str) -> bool:
        """Reuse a persisted vector store when the KB is unchanged."""
        try:
            if not self.vector_store_path.exists() or not self.kb_manifest_path.exists():
                return False

            manifest = json.loads(self.kb_manifest_path.read_text(encoding='utf-8'))
            if manifest.get('kb_hash') != kb_hash:
                return False

            self.vector_store = Chroma(
                persist_directory=str(self.vector_store_path),
                embedding_function=self.embeddings
            )
            logger.info("✅ Reused cached vector store from previous startup")
            return True
        except Exception as exc:
            logger.warning(f"Cached vector store load failed, rebuilding: {exc}")
            return False

    def _save_kb_manifest(self, kb_hash: str, chunk_count: int) -> None:
        """Persist KB fingerprint for future startup reuse."""
        try:
            self.vector_store_path.mkdir(parents=True, exist_ok=True)
            payload = {
                'kb_hash': kb_hash,
                'chunk_count': chunk_count,
                'updated_at': datetime.now().isoformat(),
            }
            self.kb_manifest_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        except Exception as exc:
            logger.warning(f"Unable to persist KB manifest: {exc}")

    def _compose_telemetry_prompt(
        self,
        task: str,
        anomaly_summary: Dict,
        root_causes: List[Tuple[str, float]],
        affected_channels: List[str],
        user_question: Optional[str] = None,
        evidence_documents: Optional[List[Document]] = None,
    ) -> str:
        """Compose a telemetry-grounded prompt for Ollama."""
        evidence_documents = evidence_documents or []
        evidence_text = "\n\n".join(
            f"SOURCE: {doc.metadata.get('source', 'Unknown')}"
            f"\nTOPIC: {doc.metadata.get('topic', 'general')}"
            f"\nCONTENT:\n{doc.page_content.strip()}"
            for doc in evidence_documents
        ) or "No additional evidence retrieved."

        root_cause_lines = "\n".join(
            f"- {fault_id} ({confidence:.2%})" for fault_id, confidence in root_causes[:5]
        ) or "- No root causes identified yet"

        return f"""You are an ADCS satellite telemetry diagnosis assistant.

Task: {task}

Operational context:
- Subsystem: Attitude Determination and Control System (ADCS)
- Affected channels: {', '.join(affected_channels) or 'Unknown'}
- Anomaly probability: {float(anomaly_summary.get('probability', 0.0)):.2%}
- Severity: {anomaly_summary.get('severity', 'UNKNOWN')}
- Characteristics: {', '.join(anomaly_summary.get('characteristics', [])) or 'none detected'}
- Timestamp: {anomaly_summary.get('timestamp', 'N/A')}

Probable root causes from the knowledge graph:
{root_cause_lines}

Evidence from the telemetry knowledge base:
{evidence_text}

Instructions:
- Use only the provided telemetry context and evidence.
- Be technically precise and explain uncertainty when present.
- If the evidence is insufficient, say so explicitly and recommend the next verification step.
- Prefer the 7 core ADCS manuals and procedures over generic background text when they are relevant.
- When possible, cite a specific operational manual, anomaly catalogue, FDIR procedure, RCA framework, corrective-action reference, feature guide, or environment-effects reference.
- If a retrieved chunk has section metadata, reference it in the answer so the operator can trace the source more precisely.
- Return concise operator-friendly guidance, not generic filler.

User question: {user_question or 'Generate a diagnosis summary.'}
"""

    def _deterministic_fallback(
        self,
        anomaly_summary: Dict,
        root_causes: List[Tuple[str, float]],
        affected_channels: List[str],
        question: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate a structured fallback explanation when Ollama is unavailable."""
        top_causes = [f"{fault_id} ({confidence:.2%})" for fault_id, confidence in root_causes[:3]]
        explanation_parts = [
            f"ADCS telemetry shows an anomaly probability of {float(anomaly_summary.get('probability', 0.0)):.1%}.",
            f"Affected channels: {', '.join(affected_channels) or 'unknown'}.",
        ]
        if top_causes:
            explanation_parts.append(f"Top probable causes: {', '.join(top_causes)}.")
        if question:
            explanation_parts.append(f"Question addressed: {question}")
        explanation_parts.append(
            "Recommended next steps: verify sensor calibration, compare channel trends, and inspect ADCS control-loop stability."
        )

        return {
            'response': ' '.join(explanation_parts),
            'actions': [
                'Verify magnetometer and photodiode calibration',
                'Inspect ADCS control loop stability and actuator response',
                'Increase telemetry sampling and compare adjacent channel trends'
            ],
            'confidence': float(max(anomaly_summary.get('probability', 0.0), 1.0 - anomaly_summary.get('probability', 0.0))),
            'method': 'deterministic_fallback',
            'explanation_mode': 'deterministic_fallback',
            'source_references': ['ADCS fallback playbook'],
        }
    
    def generate_explanation(
        self,
        anomaly_summary: Dict,
        root_causes: List[RootCause],
        affected_channels: List[str]
    ) -> Dict[str, str]:
        """
        Generate comprehensive explanation for detected anomaly
        
        Args:
            anomaly_summary: Dictionary with anomaly detection results
            root_causes: List of (fault_id, confidence) from knowledge graph
            affected_channels: List of anomalous channel IDs
            
        Returns:
            Dictionary with explanation, corrective actions, severity, and evidence metadata
        """
        with LogContext("Generating fault diagnosis explanation"):
            
            normalized_root_causes = self._normalize_root_causes(root_causes)
            self._ensure_llm_ready()
            evidence_documents = self._retrieve_evidence_documents(
                f"ADCS anomaly probability {anomaly_summary.get('probability', 0.0):.2%} "
                f"channels {', '.join(affected_channels)} causes {', '.join([rc[0] for rc in normalized_root_causes[:3]])}"
            )

            # Build context for LLM
            context = self._build_diagnosis_context(
                anomaly_summary, normalized_root_causes, affected_channels
            )
            
            # Generate question for RAG
            question = (
                f"Explain the detected anomaly in satellite ADCS telemetry for channels {', '.join(affected_channels)}. "
                f"The probable root causes are: {', '.join([rc[0] for rc in normalized_root_causes[:3]])}. "
                f"Provide detailed diagnosis and corrective actions."
            )
            
            prompt = self._compose_telemetry_prompt(
                task="Generate a diagnosis explanation and corrective actions.",
                anomaly_summary=anomaly_summary,
                root_causes=normalized_root_causes,
                affected_channels=affected_channels,
                evidence_documents=evidence_documents,
            )

            explanation_mode = 'deterministic_fallback'
            if self.llm is not None:
                try:
                    explanation = self.llm.invoke(prompt)
                    source_docs = evidence_documents
                    explanation_mode = 'ollama_rag' if evidence_documents else 'ollama_direct'
                except Exception as e:
                    logger.warning(f"Ollama response failed: {e}")
                    fallback = self._deterministic_fallback(anomaly_summary, normalized_root_causes, affected_channels, question)
                    explanation = fallback['response']
                    source_docs = []
                    explanation_mode = fallback['explanation_mode']
            else:
                fallback = self._deterministic_fallback(anomaly_summary, normalized_root_causes, affected_channels, question)
                explanation = fallback['response']
                source_docs = []
                explanation_mode = fallback['explanation_mode']
            
            # Extract corrective actions
            corrective_actions = self._extract_corrective_actions(
                normalized_root_causes, affected_channels
            )
            
            # Assess severity
            severity = self._assess_severity(anomaly_summary, normalized_root_causes)
            
            result = {
                'explanation': explanation,
                'corrective_actions': corrective_actions,
                'severity': severity,
                'confidence': float(max(
                    float(anomaly_summary.get('probability', 0.0) or 0.0),
                    normalized_root_causes[0][1] if normalized_root_causes else 0.0
                )),
                'source_references': self._format_source_references(source_docs),
                'explanation_mode': explanation_mode,
                'evidence_summary': {
                    'affected_channels': affected_channels,
                    'probable_root_causes': [
                        {
                            'fault_id': fault_id,
                            'confidence': confidence
                        }
                        for fault_id, confidence in normalized_root_causes[:5]
                    ],
                    'anomaly_probability': float(anomaly_summary.get('probability', 0.0)),
                    'timestamp': anomaly_summary.get('timestamp')
                }
            }
            
            logger.info(f"✅ Explanation generated - Severity: {severity}")
            return result

    def chat_diagnosis(
        self,
        message: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Union[str, float, List[str], Dict]]:
        """Answer an operator question using telemetry-grounded context and RAG when available."""
        context = context or {}
        detection = context.get('detection', {})
        root_causes = context.get('root_causes', [])
        channel = context.get('channel', 'Unknown')
        features = context.get('features', {})
        chat_history = context.get('chat_history', [])

        normalized_root_causes = self._normalize_root_causes(root_causes)
        self._ensure_llm_ready()
        anomaly_summary = {
            'probability': float(detection.get('probability', 0.0) or 0.0),
            'severity': detection.get('severity', 'UNKNOWN'),
            'characteristics': detection.get('characteristics', []),
            'timestamp': context.get('timestamp') or detection.get('timestamp')
        }

        history_block = "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}"
            for item in chat_history[-6:]
            if isinstance(item, dict)
        )

        query = (
            f"Channel {channel}. Question: {message}. "
            f"Detection probability {anomaly_summary['probability']:.2%}, severity {anomaly_summary['severity']}. "
            f"Root causes: {', '.join([rc[0] for rc in normalized_root_causes[:3]]) or 'none'}. "
            f"Recent dialogue: {history_block or 'none'}."
        )
        evidence_documents = self._retrieve_evidence_documents(query)

        if self.llm is not None:
            try:
                prompt = self._compose_telemetry_prompt(
                    task="Answer the operator question using the diagnosis context.",
                    anomaly_summary=anomaly_summary,
                    root_causes=normalized_root_causes,
                    affected_channels=[channel] if channel != 'Unknown' else context.get('affected_channels', []),
                    user_question=message,
                    evidence_documents=evidence_documents,
                )
                response_text = self.llm.invoke(prompt)
                mode = 'ollama_rag' if evidence_documents else 'ollama_direct'
            except Exception as exc:
                logger.warning(f"Ollama chat failed: {exc}")
                fallback = self._deterministic_fallback(anomaly_summary, normalized_root_causes, [channel], message)
                response_text = fallback['response']
                mode = fallback['explanation_mode']
                evidence_documents = []
        else:
            fallback = self._deterministic_fallback(anomaly_summary, normalized_root_causes, [channel], message)
            response_text = fallback['response']
            mode = fallback['explanation_mode']
            evidence_documents = []

        corrective_actions = self._extract_corrective_actions(normalized_root_causes, [channel])
        if features:
            corrective_actions.insert(0, "Review the feature trends and compare them with nominal telemetry baselines")

        return {
            'response': response_text,
            'actions': corrective_actions[:5],
            'confidence': float(normalized_root_causes[0][1] if normalized_root_causes else anomaly_summary['probability']),
            'method': mode,
            'explanation_mode': mode,
            'source_references': self._format_source_references(evidence_documents) if evidence_documents else ['ADCS fallback playbook'],
            'evidence_summary': {
                'affected_channels': [channel] if channel != 'Unknown' else context.get('affected_channels', []),
                'probable_root_causes': [
                    {'fault_id': fault_id, 'confidence': confidence}
                    for fault_id, confidence in normalized_root_causes[:5]
                ],
                'anomaly_probability': anomaly_summary['probability'],
                'timestamp': anomaly_summary.get('timestamp')
            }
        }
    
    def _normalize_root_causes(self, root_causes: List[RootCause]) -> List[Tuple[str, float]]:
        """Normalize root causes into (fault_id, confidence) pairs."""
        normalized: List[Tuple[str, float]] = []

        for rc in root_causes:
            if isinstance(rc, dict):
                fault_id = str(
                    rc.get('fault_id')
                    or rc.get('fault_name')
                    or rc.get('fault')
                    or 'unknown_fault'
                )
                try:
                    confidence = float(rc.get('confidence', 0.0) or 0.0)
                except (TypeError, ValueError):
                    confidence = 0.0
                normalized.append((fault_id, confidence))
            elif isinstance(rc, (list, tuple)) and rc:
                fault_id = str(rc[0])
                try:
                    confidence = float(rc[1]) if len(rc) > 1 else 0.0
                except (TypeError, ValueError):
                    confidence = 0.0
                normalized.append((fault_id, confidence))

        return normalized

    def _build_diagnosis_context(
        self,
        anomaly_summary: Dict,
        root_causes: List[Tuple[str, float]],
        affected_channels: List[str]
    ) -> str:
        """Build structured context for LLM"""
        context = f"""
ANOMALY DETECTION SUMMARY:
- Anomaly Probability: {anomaly_summary.get('probability', 0.0):.2%}
- Affected Channels: {', '.join(affected_channels)}
- Detection Timestamp: {anomaly_summary.get('timestamp', 'N/A')}

KNOWLEDGE GRAPH ANALYSIS - PROBABLE ROOT CAUSES:
"""
        for i, (fault_id, confidence) in enumerate(root_causes, 1):
            context += f"\n{i}. {fault_id} (Confidence: {confidence:.2%})"
        
        context += f"\n\nSUBSYSTEMS AFFECTED:\n"
        context += "- ADCS (Attitude Determination and Control System)\n"
        
        return context
    
    def _generate_direct_explanation(self, context: str, question: str) -> str:
        """Generate explanation without RAG (fallback)"""
        prompt = f"{context}\n\nQuestion: {question}\n\nAnswer:"
        explanation = self.llm.invoke(prompt)
        return explanation
    
    def _extract_corrective_actions(
        self,
        root_causes: List[Tuple[str, float]],
        affected_channels: List[str]
    ) -> List[str]:
        """Extract specific corrective actions based on root causes"""
        actions = []
        
        fault_actions_map = {
            'sensor_bias': [
                "Recalibrate affected sensors using on-orbit calibration procedures",
                "Update bias compensation parameters in the flight software",
                "Monitor long-term trend to assess bias stability"
            ],
            'sensor_noise': [
                "Check power supply stability to sensors",
                "Review sensor grounding and shielding",
                "Consider applying software filtering with higher cutoff"
            ],
            'sensor_drift': [
                "Perform sensor recalibration sequence",
                "Update drift compensation model",
                "Schedule more frequent calibration cycles"
            ],
            'sensor_saturation': [
                "Check for excessive environmental inputs (magnetic field, sun intensity)",
                "Verify sensor dynamic range settings",
                "Consider attitude maneuver to reduce input magnitude"
            ],
            'power_anomaly': [
                "Check power bus voltage and current",
                "Verify power distribution to ADCS subsystem",
                "Switch to redundant power channel if available"
            ],
            'thermal_anomaly': [
                "Check thermal control system status",
                "Review sensor temperature telemetry",
                "Adjust spacecraft attitude for thermal stability"
            ],
            'communication_error': [
                "Verify telemetry downlink signal quality",
                "Check for data packet corruption or loss",
                "Request telemetry retransmission if possible"
            ]
        }
        
        for fault_id, confidence in root_causes[:2]:  # Top 2 causes
            if fault_id in fault_actions_map:
                actions.extend(fault_actions_map[fault_id])
        
        # Generic actions
        actions.append(f"Continue monitoring telemetry from channels: {', '.join(affected_channels)}")
        actions.append("Log anomaly event in spacecraft operations log")
        
        return list(dict.fromkeys(actions))  # Remove duplicates while preserving order
    
    def _assess_severity(
        self,
        anomaly_summary: Dict,
        root_causes: List[Tuple[str, float]]
    ) -> str:
        """Assess severity level of the anomaly"""
        probability = anomaly_summary.get('probability', 0.0)
        
        # Critical fault types
        critical_faults = {'power_anomaly', 'sensor_saturation'}
        
        # Check if any critical fault is in top causes
        has_critical = any(
            fault_id in critical_faults 
            for fault_id, _ in root_causes[:2]
        )
        
        if probability >= 0.9 or has_critical:
            return "CRITICAL"
        elif probability >= 0.75:
            return "HIGH"
        elif probability >= 0.5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def save_vector_store(self):
        """Persist vector store to disk"""
        if self.vector_store:
            self.vector_store.persist()
            logger.info(f"💾 Vector store persisted to {self.vector_store_path}")
    
    @classmethod
    def load_from_disk(cls, vector_store_path: Path) -> 'DiagnosisExplainer':
        """Load explainer with existing vector store"""
        explainer = cls(vector_store_path=vector_store_path)
        
        explainer.vector_store = Chroma(
            persist_directory=str(vector_store_path),
            embedding_function=explainer.embeddings
        )
        
        explainer.initialize_qa_chain()
        
        logger.info(f"📂 DiagnosisExplainer loaded from {vector_store_path}")
        return explainer


def create_knowledge_base_documents() -> List[Dict[str, str]]:
    """
    Create knowledge base documents for RAG.

    Sources:
    1) Curated ADCS diagnosis guidance embedded in code.
    2) Text/markdown documents from project docs and research folders.
    """
    documents = [
        {
            'content': """
            ADCS Sensor Bias:
            A sensor bias is a constant offset in sensor readings that persists over time. 
            For magnetometers, bias can be caused by residual spacecraft magnetic fields, 
            sensor electronics drift, or calibration errors. For photodiodes, bias can result 
            from dark current variations or amplifier offset.
            
            Diagnosis: Compare readings across multiple axes/sensors to identify consistent offset.
            Resolution: Perform on-orbit calibration using known reference (Earth's magnetic field model 
            or sun vector). Update bias compensation parameters in flight software.
            """,
            'metadata': {'source': 'ADCS_Operations_Manual', 'topic': 'sensor_bias'}
        },
        {
            'content': """
            ADCS Power Anomalies:
            Power anomalies in ADCS can manifest as voltage fluctuations, current spikes, or 
            undervoltage conditions affecting sensor performance. Photodiodes are particularly 
            sensitive to power supply stability.
            
            Symptoms: Erratic sensor readings, increased noise, sensor dropouts.
            Diagnosis: Correlate sensor anomalies with power bus telemetry.
            Resolution: Check power distribution, switch to redundant power channel, 
            investigate upstream power system issues.
            """,
            'metadata': {'source': 'Power_Systems_Handbook', 'topic': 'power_anomaly'}
        },
        {
            'content': """
            Magnetometer Thermal Effects:
            Magnetometers exhibit temperature-dependent behavior. Temperature variations can cause
            changes in sensor sensitivity, offset, and noise characteristics.
            
            Diagnosis: Correlate magnetometer anomalies with thermal telemetry. Look for 
            patterns matching orbital thermal cycles.
            Resolution: Apply temperature compensation models. Adjust spacecraft attitude to 
            stabilize thermal environment. Update thermal calibration coefficients.
            """,
            'metadata': {'source': 'Sensor_Calibration_Guide', 'topic': 'thermal_anomaly'}
        },
        {
            'content': """
            Photodiode Sun Sensor Operation:
            Photodiodes measure incident solar radiation to determine sun vector direction.
            Normal operation shows clear day/night cycles and systematic variations as spacecraft 
            attitude changes. Anomalies include unexpected saturation, reduced sensitivity, 
            or asymmetric response across sensor array.
            
            Common Issues:
            - Contamination reducing sensitivity
            - Degradation from radiation exposure
            - Shadowing from spacecraft structures
            - Power supply instability
            """,
            'metadata': {'source': 'Sun_Sensor_Operations', 'topic': 'photodiode'}
        },
        {
            'content': """
            ADCS Anomaly Response Procedures:
            
            CRITICAL Severity:
            1. Notify Mission Control immediately
            2. Assess impact on spacecraft safety and mission operations
            3. Implement safe mode if attitude control is compromised
            4. Begin detailed troubleshooting with engineering team
            
            HIGH Severity:
            1. Increase telemetry monitoring frequency
            2. Schedule engineering analysis session
            3. Prepare contingency procedures
            4. Consider switching to redundant systems
            
            MEDIUM/LOW Severity:
            1. Log event in operations timeline
            2. Continue nominal operations with enhanced monitoring
            3. Schedule routine investigation during next planning cycle
            """,
            'metadata': {'source': 'Operations_Procedures', 'topic': 'response_procedures'}
        },
        {
            'content': """
            Magnetometer Telemetry Interpretation:
            The magnetometer channels CADC0872, CADC0873, and CADC0874 represent the X, Y, and Z
            axis magnetic field measurements. Useful anomaly indicators include mean shift,
            rising variance, increased peak count, and abrupt changes in first or second order
            derivative statistics. A consistent offset across axes often suggests calibration drift,
            while oscillation or strong derivative spikes can indicate disturbance torques or control
            instability.
            """,
            'metadata': {'source': 'Telemetry_Interpretation_Guide', 'topic': 'magnetometer_context'}
        },
        {
            'content': """
            Photodiode Telemetry Interpretation:
            The photodiode channels CADC0875 through CADC0880 are used for sun-vector estimation.
            They are sensitive to power fluctuations, shielding, contamination, and attitude changes.
            When diagnosing anomalies, compare channel symmetry, temporal stability, and variance.
            Unexpected dropouts or large spread across the photodiode array can indicate power issues,
            sensor degradation, or misalignment in the ADCS observation frame.
            """,
            'metadata': {'source': 'Telemetry_Interpretation_Guide', 'topic': 'photodiode_context'}
        },
        {
            'content': """
            Diagnosis Workflow for Satellite Telemetry:
            1. Confirm anomaly detection probability and severity.
            2. Identify affected channels and extract feature characteristics.
            3. Consult the knowledge graph for likely root causes and confidence values.
            4. Retrieve relevant operational guidance and compare against mission context.
            5. Provide a concise response with evidence, uncertainty, and next actions.
            The explanation should state when evidence is incomplete and avoid overclaiming.
            """,
            'metadata': {'source': 'Diagnosis_Workflow_Guide', 'topic': 'workflow'}
        }
    ]

    # Load project-specific context from local files.
    external_dirs = [
        settings.BASE_DIR / "docs",
        settings.BASE_DIR / "research papers",
    ]
    max_external_chars = 12000
    supported_extensions = {".md", ".txt", ".rst", ".pdf"}
    external_documents: List[Dict[str, str]] = []

    for base_dir in external_dirs:
        if not base_dir.exists():
            continue

        for path in sorted(base_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in supported_extensions:
                continue

            if path.suffix.lower() == '.pdf':
                if PdfReader is None:
                    logger.warning(f"Skipping PDF KB file {path}: pypdf is not installed")
                    continue
                try:
                    reader = PdfReader(str(path))
                    page_texts = []
                    for page in reader.pages:
                        page_text = page.extract_text() or ''
                        if page_text:
                            page_texts.append(page_text)
                    content = "\n".join(page_texts).strip()
                except Exception as exc:
                    logger.warning(f"Skipping PDF KB file {path}: {exc}")
                    continue
            else:
                try:
                    content = path.read_text(encoding='utf-8', errors='ignore').strip()
                except Exception as exc:
                    logger.warning(f"Skipping KB file {path}: {exc}")
                    continue

            if len(content) < 200:
                # Ignore tiny files that add noise but little retrieval value.
                continue

            if len(content) > max_external_chars:
                content = content[:max_external_chars]

            external_documents.append({
                'content': content,
                'metadata': {
                    'source': str(path.relative_to(settings.BASE_DIR)).replace('\\', '/'),
                    **self._section_metadata_for_source(str(path.relative_to(settings.BASE_DIR)).replace('\\', '/')),
                }
            })

    if external_documents:
        source_counts = Counter(doc['metadata']['source'].split('/')[0] for doc in external_documents)
        logger.info(
            f"Loaded {len(external_documents)} external KB documents from docs/research folders: "
            f"{dict(source_counts)}"
        )
        documents.extend(external_documents)
    else:
        logger.warning("No external docs found in docs/ or research papers/; using curated ADCS KB only")
    
    return documents
