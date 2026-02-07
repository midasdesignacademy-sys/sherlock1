"""
SHERLOCK - Pytest fixtures and mocks.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.state import create_initial_state


@pytest.fixture
def sample_uploads(tmp_path):
    """Temporary directory with sample TXT files."""
    (tmp_path / "doc1.txt").write_text(
        "Reunião entre João Silva e Maria Santos. Data: 15/01/2024. TechCorp. joao@tech.com.",
        encoding="utf-8",
    )
    (tmp_path / "doc2.txt").write_text(
        "Contrato TechCorp e InnovaTech. Maria Santos. 20/01/2024. R$ 500.000.",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def initial_state(sample_uploads):
    """Initial state with config pointing to sample uploads."""
    state = create_initial_state()
    state["config"] = {"uploads_path": str(sample_uploads)}
    return state


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j client to avoid requiring Docker (patch where used in graph_builder)."""
    with patch("knowledge_graph.graph_builder.Neo4jClient") as m:
        instance = MagicMock()
        instance.connect = MagicMock()
        instance.close = MagicMock()
        instance.create_entity_node = MagicMock()
        instance.create_relationship = MagicMock()
        instance.get_graph_stats = MagicMock(return_value={
            "node_count": 0, "relationship_count": 0, "edge_count": 0, "entity_types": {}
        })
        instance.get_centrality_scores = MagicMock(return_value={})
        instance.detect_communities = MagicMock(return_value={})
        instance.get_betweenness = MagicMock(return_value={})
        m.return_value = instance
        yield m


@pytest.fixture
def mock_chroma():
    """Mock Chroma to use in-memory or avoid server."""
    with patch("rag.vector_store.get_chroma_client") as m:
        try:
            import chromadb
            client = chromadb.Client()
            m.return_value = client
        except Exception:
            m.return_value = MagicMock()
        yield m
