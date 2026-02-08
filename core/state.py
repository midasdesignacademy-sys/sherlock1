"""
SHERLOCK Intelligence System - State Management
Defines the state structure for LangGraph multi-agent workflow.
"""

from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata for ingested documents (Soul-aligned)."""
    doc_id: str
    filename: str
    file_type: str
    file_hash: str
    size_bytes: int
    upload_timestamp: datetime
    source: Optional[str] = None
    language: Optional[str] = None
    page_count: Optional[int] = None
    author: Optional[str] = None
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    file_path: Optional[str] = None
    status: str = "success"
    extraction_method: Optional[str] = None
    ocr_confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    priority_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentClassification(BaseModel):
    """Classification results (Soul-aligned): doc_type, domain, language, priority_score, reasons, processing_order."""
    doc_id: str
    domain: str
    document_type: str
    language: str
    priority_score: float
    suspicious_patterns: List[str] = Field(default_factory=list)
    doc_type_confidence: float = 0.0
    domain_confidence: float = 0.0
    language_confidence: float = 0.0
    priority_reasons: List[str] = Field(default_factory=list)
    keywords_detected: List[str] = Field(default_factory=list)
    estimated_relevance: str = "medium"
    processing_order: int = 0


class Entity(BaseModel):
    """Extracted entity with metadata (Soul-compatible)."""
    entity_id: str
    text: str
    entity_type: str
    doc_id: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    confidence: float = 1.0
    normalized_text: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    documents: List[str] = Field(default_factory=list)
    frequency: int = 0
    contexts: List[str] = Field(default_factory=list)
    variations: List[str] = Field(default_factory=list)


class Relationship(BaseModel):
    """Relationship between two entities (Soul: source, target, type, evidence_count, confidence)."""
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    weight: float = 1.0
    evidence_doc_ids: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    context: Optional[str] = None
    confidence: float = 1.0


class SemanticLink(BaseModel):
    """Semantic connection between documents (Soul: doc1, doc2, similarity, shared_entities, shared_concepts)."""
    doc_id_1: str
    doc_id_2: str
    similarity_score: float
    link_type: str = "semantic"
    rationale: Optional[str] = None
    common_entities: List[str] = Field(default_factory=list)
    shared_entities: List[str] = Field(default_factory=list)
    shared_concepts: List[str] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    """Event (Soul: event_id, date, type, description, entities, documents, confidence)."""
    event_id: str
    timestamp: Optional[datetime] = None
    inferred_timestamp: Optional[datetime] = None
    timestamp_confidence: float = 0.0
    description: str
    entities_involved: List[str] = Field(default_factory=list)
    source_doc_ids: List[str] = Field(default_factory=list)
    date: Optional[str] = None
    type: str = "EVENT"


class CryptoSegment(BaseModel):
    """Detected encrypted or obfuscated content."""
    segment_id: str
    doc_id: str
    content: str
    start_pos: int
    end_pos: int
    crypto_type: str
    confidence: float
    decrypted_content: Optional[str] = None


class CryptographyFinding(BaseModel):
    """Soul Agent 4: cryptography_findings schema."""
    document_id: str
    finding_type: str
    location: Optional[str] = None
    encoded_text: Optional[str] = None
    decoded_preview: Optional[str] = None
    confidence: float = 0.0
    algorithm: Optional[str] = None


class Pattern(BaseModel):
    """Detected pattern (Soul: pattern_type, description, occurrences, confidence, evidence)."""
    pattern_id: str
    pattern_type: str
    description: str
    entities_involved: List[str] = Field(default_factory=list)
    doc_ids_involved: List[str] = Field(default_factory=list)
    severity: str = "medium"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    occurrences: int = 1
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)


class Hypothesis(BaseModel):
    """Investigative hypothesis (Soul: hypothesis_id, title, description, confidence, supporting_evidence, status)."""
    hypothesis_id: str
    title: Optional[str] = None
    description: str
    confidence: float
    supporting_evidence: List[str] = Field(default_factory=list)
    entities_involved: List[str] = Field(default_factory=list)
    doc_ids_supporting: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    status: str = "under_review"


class Conflict(TypedDict, total=False):
    """Spec §5: conflict_id, type (DUPLICATES|CONTRADICTIONS|AMBIGUITY), existing, new, confidence, resolution."""
    conflict_id: str
    type: str  # DUPLICATES | CONTRADICTIONS | AMBIGUITY
    existing: Dict[str, Any]
    new: Dict[str, Any]
    confidence: float
    resolution: str  # pending | MERGE | KEEP_BOTH | IGNORE


class InvestigationState(TypedDict, total=False):
    """
    Central state for the SHERLOCK investigation workflow (Soul-aligned).
    Spec §2: version, last_updated, processing_queue, delta_log, conflicts for incremental.
    """
    raw_documents: List[Dict[str, Any]]
    processed_docs: List[Dict[str, Any]]
    document_metadata: Dict[str, Any]
    classifications: Dict[str, Any]
    extracted_text: Dict[str, str]
    entities: Any
    relationships: List[Any]
    entity_registry: Dict[str, List[str]]
    encrypted_segments: List[Any]
    cryptography_findings: List[Any]
    decrypted_content: Dict[str, str]
    semantic_links: List[Any]
    contradictions: List[Dict[str, Any]]
    narrative_threads: List[Dict[str, Any]]
    timeline: List[Any]
    temporal_anomalies: List[Dict[str, Any]]
    causal_chains: List[Dict[str, Any]]
    patterns: List[Any]
    outliers: List[str]
    anomalies: List[Dict[str, Any]]
    graph_metadata: Dict[str, Any]
    centrality_scores: Dict[str, float]
    communities: Dict[int, List[str]]
    hypotheses: List[Any]
    leads: List[Dict[str, Any]]
    report_summary: Optional[str]
    odos_status: str
    odos_violations: List[Dict[str, Any]]
    delta_e: float
    guardian_delta_e: float
    fidelity: float
    rcf: float
    compliance_report: Dict[str, Any]
    current_step: str
    iteration_count: int
    human_feedback: Optional[str]
    error_log: List[str]
    config: Dict[str, Any]
    # Spec §2 - Estado evolutivo (incremental)
    version: int
    last_updated: Optional[str]
    processing_queue: List[str]
    delta_log: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]


def create_initial_state(config_override: Optional[Dict[str, Any]] = None) -> InvestigationState:
    """Create a fresh investigation state with default values (Soul-aligned)."""
    return InvestigationState(
        raw_documents=[],
        processed_docs=[],
        document_metadata={},
        classifications={},
        extracted_text={},
        entities={},
        relationships=[],
        entity_registry={},
        encrypted_segments=[],
        cryptography_findings=[],
        decrypted_content={},
        semantic_links=[],
        contradictions=[],
        narrative_threads=[],
        timeline=[],
        temporal_anomalies=[],
        causal_chains=[],
        patterns=[],
        outliers=[],
        anomalies=[],
        graph_metadata={},
        centrality_scores={},
        communities={},
        hypotheses=[],
        leads=[],
        report_summary=None,
        odos_status="PENDING",
        odos_violations=[],
        delta_e=0.0,
        guardian_delta_e=0.0,
        fidelity=0.0,
        rcf=0.0,
        compliance_report={},
        current_step="initialization",
        iteration_count=0,
        human_feedback=None,
        error_log=[],
        config=config_override or {},
        version=1,
        last_updated=None,
        processing_queue=[],
        delta_log=[],
        conflicts=[],
    )
