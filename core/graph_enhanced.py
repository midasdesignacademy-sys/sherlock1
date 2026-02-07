"""
SHERLOCK - Monitored workflow: same graph with activity emission for real-time UI.
"""

from langgraph.graph import StateGraph, END
from loguru import logger

from core.state import InvestigationState, create_initial_state
from core.monitors import ActivityMonitor
from core.graph import (
    _after_guardian_route,
    create_sherlock_graph,
    _print_summary,
)
from agents.ingestion import DocumentIngestionAgent
from agents.classifier import DocumentClassifierAgent
from agents.entity_extractor import EntityExtractionAgent
from agents.semantic_linker import SemanticLinkerAgent
from agents.timeline import TimelineReconstructorAgent
from agents.cryptanalysis_agent import CryptanalysisHunterAgent
from agents.pattern_recognition import PatternRecognitionAgent
from agents.knowledge_graph import process as build_knowledge_graph
from agents.synthesis import IntelligenceSynthesisAgent
from agents.odos_guardian import process as odos_guardian_process
from core.config import settings


def wrap_agent(agent_name: str, process_fn):
    """Wrap an agent's process function to emit start/end to ActivityMonitor."""

    def wrapped(state: InvestigationState) -> InvestigationState:
        monitor = ActivityMonitor()
        monitor.emit(agent_name, "start", docs=len(state.get("document_metadata", {})))
        try:
            out = process_fn(state)
            monitor.emit(agent_name, "end", docs=len(out.get("document_metadata", {})))
            return out
        except Exception as e:
            monitor.emit(agent_name, "error", error=str(e))
            raise

    return wrapped


def create_monitored_graph():
    """Build the same workflow as create_sherlock_graph but with monitored nodes."""
    workflow = StateGraph(InvestigationState)

    ingestion_agent = DocumentIngestionAgent()
    classifier_agent = DocumentClassifierAgent()
    entity_agent = EntityExtractionAgent()
    crypto_agent = CryptanalysisHunterAgent()
    semantic_agent = SemanticLinkerAgent()
    timeline_agent = TimelineReconstructorAgent()
    pattern_agent = PatternRecognitionAgent()
    synthesis_agent = IntelligenceSynthesisAgent()

    workflow.add_node("ingest_documents", wrap_agent("ingest_documents", ingestion_agent.process))
    workflow.add_node("classify_documents", wrap_agent("classify_documents", classifier_agent.process))
    workflow.add_node("extract_entities", wrap_agent("extract_entities", entity_agent.process))
    workflow.add_node("cryptanalysis_hunter", wrap_agent("cryptanalysis_hunter", crypto_agent.process))
    workflow.add_node("semantic_linker", wrap_agent("semantic_linker", semantic_agent.process))
    workflow.add_node("timeline", wrap_agent("timeline", timeline_agent.process))
    workflow.add_node("pattern_recognition", wrap_agent("pattern_recognition", pattern_agent.process))
    workflow.add_node("build_knowledge_graph", wrap_agent("build_knowledge_graph", build_knowledge_graph))
    workflow.add_node("synthesis", wrap_agent("synthesis", synthesis_agent.process))
    workflow.add_node("odos_guardian", wrap_agent("odos_guardian", odos_guardian_process))

    workflow.set_entry_point("ingest_documents")
    workflow.add_edge("ingest_documents", "classify_documents")
    workflow.add_edge("classify_documents", "extract_entities")
    workflow.add_edge("extract_entities", "cryptanalysis_hunter")
    workflow.add_edge("cryptanalysis_hunter", "semantic_linker")
    workflow.add_edge("semantic_linker", "timeline")
    workflow.add_edge("timeline", "pattern_recognition")
    workflow.add_edge("pattern_recognition", "build_knowledge_graph")
    workflow.add_edge("build_knowledge_graph", "synthesis")
    workflow.add_edge("synthesis", "odos_guardian")
    workflow.add_conditional_edges("odos_guardian", _after_guardian_route, {"report": END, "refinement": END})

    return workflow.compile()


def run_monitored_investigation(documents_path: str = None) -> InvestigationState:
    """Run investigation with activity monitoring; returns final state."""
    logger.info("SHERLOCK - Starting monitored investigation")
    ActivityMonitor().clear()
    initial = create_initial_state()
    if documents_path:
        initial["config"] = initial.get("config") or {}
        initial["config"]["uploads_path"] = documents_path
    app = create_monitored_graph()
    final_state = app.invoke(initial)
    _print_summary(final_state)
    return final_state
