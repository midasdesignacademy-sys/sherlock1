"""
Unit tests for SHERLOCK agents (Fase 1).
"""

import pytest
from pathlib import Path
import tempfile
from datetime import datetime

from core.state import (
    create_initial_state,
    InvestigationState,
    DocumentMetadata,
    DocumentClassification,
    Entity,
    Relationship,
)
from core.config import settings


@pytest.fixture
def initial_state():
    return create_initial_state()


@pytest.fixture
def sample_txt_dir(tmp_path):
    (tmp_path / "doc1.txt").write_text(
        "Reunião entre João Silva e Maria Santos. Data: 15/01/2024. "
        "TechCorp. Contato: joao@techcorp.com.br. Valor R$ 500.000.",
        encoding="utf-8",
    )
    (tmp_path / "doc2.txt").write_text(
        "Contrato TechCorp e InnovaTech. Maria Santos. 20/01/2024. R$ 500.000.",
        encoding="utf-8",
    )
    return tmp_path


def test_create_initial_state(initial_state):
    assert initial_state["raw_documents"] == []
    assert initial_state["document_metadata"] == {}
    assert initial_state["entities"] == {}
    assert initial_state["relationships"] == []
    assert initial_state["current_step"] == "initialization"
    assert initial_state["odos_status"] == "PENDING"


def test_ingestion_agent(sample_txt_dir, initial_state):
    from agents.ingestion import DocumentIngestionAgent
    initial_state["config"] = {"uploads_path": str(sample_txt_dir)}
    agent = DocumentIngestionAgent()
    state = agent.process(initial_state)
    assert len(state["document_metadata"]) >= 1
    assert len(state["extracted_text"]) >= 1
    assert len(state["processed_docs"]) >= 1
    assert state["current_step"] == "ingestion_complete"
    for doc_id, text in state["extracted_text"].items():
        assert isinstance(text, str)
        assert len(text) > 0


def test_classifier_agent(initial_state):
    from agents.classifier import DocumentClassifierAgent
    initial_state["extracted_text"] = {
        "d1": "Contrato de prestação de serviços. Cláusula 5. Valor R$ 100.000. Juiz João.",
        "d2": "Email from: a@b.com to: b@a.com. Re: Reunião.",
    }
    initial_state["document_metadata"] = {"d1": {}, "d2": {}}
    agent = DocumentClassifierAgent()
    state = agent.process(initial_state)
    assert "d1" in state["classifications"]
    assert "d2" in state["classifications"]
    assert state["current_step"] == "classification_complete"


def test_entity_extractor_agent(initial_state):
    from agents.entity_extractor import EntityExtractionAgent
    initial_state["extracted_text"] = {
        "doc1": "João Silva da TechCorp reuniu-se com Maria Santos em São Paulo em 15/01/2024. Email: joao@tech.com.",
    }
    agent = EntityExtractionAgent()
    state = agent.process(initial_state)
    assert len(state["entities"]) >= 1
    assert state["current_step"] == "entity_extraction_complete"
    assert isinstance(state["relationships"], list)


def test_entity_and_relationship_models():
    e = Entity(
        entity_id="e1",
        text="João",
        entity_type="PERSON",
        doc_id="d1",
        start_char=0,
        end_char=4,
        normalized_text="João",
    )
    assert e.entity_type == "PERSON"
    r = Relationship(
        source_entity_id="e1",
        target_entity_id="e2",
        relationship_type="co-occurrence",
        evidence_doc_ids=["d1"],
    )
    assert r.relationship_type == "co-occurrence"


def test_activity_monitor_emit_and_get_recent():
    from core.monitors import ActivityMonitor
    monitor = ActivityMonitor()
    monitor.clear()
    monitor.emit("agent1", "start", docs=0)
    monitor.emit("agent1", "end", docs=2)
    recent = monitor.get_recent(10)
    assert len(recent) == 2
    assert recent[0]["agent"] == "agent1" and recent[0]["step"] == "start"
    assert recent[1]["step"] == "end"


def test_odos_valid_empty_findings():
    from pqms.odos import validate_odos, OdosStatus
    result = validate_odos([], {})
    assert result.status == OdosStatus.VALID


def test_odos_needs_review_when_entity_without_evidence():
    from pqms.odos import validate_odos, OdosStatus
    findings = [{"entities_involved": ["e1"], "doc_ids_supporting": []}]
    state = {"relationships": []}
    result = validate_odos(findings, state)
    assert result.status == OdosStatus.NEEDS_REVIEW


def test_suggest_caesar_shift():
    from cryptanalysis.frequency import suggest_caesar_shift
    # "hello" with shift 3 is "ebiil" (caesar cipher)
    cipher = "ebiil"
    shift = suggest_caesar_shift(cipher, "en")
    assert 0 <= shift <= 25
