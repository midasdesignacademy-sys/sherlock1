"""
SHERLOCK - Knowledge Graph Agent (Agent 8).
Delegates to knowledge_graph.graph_builder.
"""

from core.state import InvestigationState
from knowledge_graph.graph_builder import KnowledgeGraphBuilder


def process(state: InvestigationState) -> InvestigationState:
    """Agent 8: Build and analyze knowledge graph from entities and relationships."""
    return KnowledgeGraphBuilder().process(state)
