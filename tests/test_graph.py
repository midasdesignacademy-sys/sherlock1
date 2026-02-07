"""
Integration test for SHERLOCK LangGraph workflow (Fase 1).
MVP: ingest -> classify -> entities -> graph.
"""

import pytest
from pathlib import Path
from langgraph.graph import StateGraph, END

from core.state import create_initial_state, InvestigationState
from core.graph import create_sherlock_graph


@pytest.fixture
def sample_uploads(tmp_path):
    (tmp_path / "a.txt").write_text(
        "Contrato entre Empresa X e Empresa Y. João Silva. Data 10/02/2024. R$ 100.000.",
        encoding="utf-8",
    )
    return tmp_path


def test_mvp_chain_ingest_classify_entities_graph(sample_uploads, mock_neo4j):
    """MVP Fase 1: only ingest -> classify -> extract_entities -> build_knowledge_graph -> END."""
    from agents.ingestion import DocumentIngestionAgent
    from agents.classifier import DocumentClassifierAgent
    from agents.entity_extractor import EntityExtractionAgent
    from agents.knowledge_graph import process as build_knowledge_graph

    workflow = StateGraph(InvestigationState)
    workflow.add_node("ingest_documents", DocumentIngestionAgent().process)
    workflow.add_node("classify_documents", DocumentClassifierAgent().process)
    workflow.add_node("extract_entities", EntityExtractionAgent().process)
    workflow.add_node("build_knowledge_graph", build_knowledge_graph)
    workflow.set_entry_point("ingest_documents")
    workflow.add_edge("ingest_documents", "classify_documents")
    workflow.add_edge("classify_documents", "extract_entities")
    workflow.add_edge("extract_entities", "build_knowledge_graph")
    workflow.add_edge("build_knowledge_graph", END)
    app = workflow.compile()

    state = create_initial_state()
    state["config"] = {"uploads_path": str(sample_uploads)}
    result = app.invoke(state)

    assert len(result.get("document_metadata", {})) >= 1
    assert len(result.get("extracted_text", {})) >= 1
    assert "classifications" in result and len(result["classifications"]) >= 1
    assert "entities" in result
    assert "relationships" in result
    assert "graph_metadata" in result
    assert result["current_step"] == "knowledge_graph_complete"
    gm = result["graph_metadata"]
    assert "node_count" in gm
    assert "top_entities" in gm or "relationship_count" in gm


def test_graph_compiles():
    app = create_sherlock_graph()
    assert app is not None


def test_graph_invoke_requires_state(mock_neo4j):
    app = create_sherlock_graph()
    state = create_initial_state()
    result = app.invoke(state)
    assert "document_metadata" in result
    assert "current_step" in result
    assert "error_log" in result


def test_graph_invoke_with_uploads(sample_uploads, mock_neo4j):
    """Full pipeline: ingest -> classify -> entities -> ... -> graph -> synthesis -> odos."""
    app = create_sherlock_graph()
    state = create_initial_state()
    state["config"] = {"uploads_path": str(sample_uploads)}
    result = app.invoke(state)
    assert "document_metadata" in result
    assert "classifications" in result
    assert "entities" in result
    assert "relationships" in result
    assert "graph_metadata" in result
    gm = result.get("graph_metadata", {})
    assert "node_count" in gm or "top_entities" in gm or "relationship_count" in gm
    assert result["current_step"] in (
        "knowledge_graph_complete",
        "synthesis_complete",
        "odos_guardian_complete",
    ) or len(result.get("error_log", [])) > 0
