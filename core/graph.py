"""
SHERLOCK - LangGraph workflow with optional checkpointing.
"""

import uuid
from langgraph.graph import StateGraph, END
from loguru import logger

from core.state import InvestigationState, create_initial_state
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
from core.memory import consolidate_memories


def _after_guardian_route(state: InvestigationState) -> str:
    """Soul: VALID → report; NEEDS_REVIEW → refinement (human); BLOCKED → blocked. All go to END."""
    odos = state.get("odos_status", "PENDING")
    if odos == "VALID":
        return "report"
    if odos == "BLOCKED":
        return "blocked"
    return "refinement"


def create_sherlock_graph():
    """Full workflow through synthesis and ODOS Guardian with conditional end."""
    workflow = StateGraph(InvestigationState)

    ingestion_agent = DocumentIngestionAgent()
    classifier_agent = DocumentClassifierAgent()
    entity_agent = EntityExtractionAgent()
    crypto_agent = CryptanalysisHunterAgent()
    semantic_agent = SemanticLinkerAgent()
    timeline_agent = TimelineReconstructorAgent()
    pattern_agent = PatternRecognitionAgent()
    synthesis_agent = IntelligenceSynthesisAgent()

    workflow.add_node("ingest_documents", ingestion_agent.process)
    workflow.add_node("classify_documents", classifier_agent.process)
    workflow.add_node("extract_entities", entity_agent.process)
    workflow.add_node("cryptanalysis_hunter", crypto_agent.process)
    workflow.add_node("semantic_linker", semantic_agent.process)
    workflow.add_node("timeline", timeline_agent.process)
    workflow.add_node("pattern_recognition", pattern_agent.process)
    workflow.add_node("build_knowledge_graph", build_knowledge_graph)
    workflow.add_node("synthesis", synthesis_agent.process)
    workflow.add_node("odos_guardian", odos_guardian_process)

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
    workflow.add_conditional_edges(
        "odos_guardian",
        _after_guardian_route,
        {"report": END, "refinement": END, "blocked": END},
    )

    checkpointer = None
    if getattr(settings, "CHECKPOINT_DIR", None) and settings.CHECKPOINT_DIR:
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            db_path = settings.CHECKPOINT_DIR / "checkpoints.db"
            settings.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
            checkpointer = SqliteSaver.from_conn_string(str(db_path))
        except Exception as e:
            logger.warning(f"Checkpointer disabled: {e}")
    if checkpointer is None:
        try:
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
        except Exception:
            pass
    # Human-in-the-loop: pause before ODOS Guardian so user can review synthesis (Soul Fase 4).
    interrupt_before = getattr(settings, "INTERRUPT_BEFORE_ODOS", True)
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer
    if interrupt_before:
        compile_kwargs["interrupt_before"] = ["odos_guardian"]
    app = workflow.compile(**compile_kwargs)
    logger.info("SHERLOCK workflow compiled" + (" (interrupt before ODOS)" if interrupt_before else ""))
    return app


def run_investigation(documents_path: str = None, thread_id: str = None) -> InvestigationState:
    """Run full investigation. If thread_id given, resume from checkpoint; else start new run."""
    logger.info("SHERLOCK - Starting investigation")
    app = create_sherlock_graph()
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}
    if thread_id:
        initial = None
    else:
        initial = create_initial_state()
        if documents_path:
            initial["config"] = initial.get("config") or {}
            initial["config"]["uploads_path"] = documents_path
    final_state = app.invoke(initial, config=config)
    inv_id = config.get("configurable", {}).get("thread_id")
    # Consolidate only when run completed past ODOS (not when interrupted before Guardian).
    if inv_id and final_state.get("current_step") == "odos_guardian_complete":
        try:
            consolidate_memories(inv_id, dict(final_state))
        except Exception as e:
            logger.warning(f"Memory consolidation failed: {e}")
    _print_summary(final_state)
    return final_state


def _print_summary(state: InvestigationState) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        console.print("\n[bold cyan]Documents[/bold cyan]")
        console.print(f"  Processed: {len(state.get('document_metadata', {}))}")
        console.print("\n[bold cyan]Entities[/bold cyan]")
        entities = state.get("entities", {})
        console.print(f"  Total: {len(entities)}")
        if entities:
            types = {}
            for e in entities.values():
                t = e.get("entity_type", e.get("type", getattr(e, "entity_type", getattr(e, "type", "?"))))
                types[t] = types.get(t, 0) + 1
            table = Table()
            table.add_column("Type", style="cyan")
            table.add_column("Count", style="magenta")
            for t, c in sorted(types.items(), key=lambda x: -x[1]):
                table.add_row(t, str(c))
            console.print(table)
        console.print(f"\n[bold cyan]Relationships[/bold cyan] {len(state.get('relationships', []))}")
        gm = state.get("graph_metadata", {})
        if gm:
            console.print(f"\n[bold cyan]Knowledge Graph[/bold cyan] Nodes: {gm.get('node_count', 0)}, Edges: {gm.get('relationship_count', 0)}")
        console.print("\n[green]Neo4j Browser:[/green] http://localhost:7474")
    except Exception:
        pass
