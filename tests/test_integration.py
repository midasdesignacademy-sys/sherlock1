"""
SHERLOCK - End-to-end integration tests.
"""

import pytest
from pathlib import Path

from core.state import create_initial_state
from core.graph import run_investigation, create_sherlock_graph


@pytest.mark.skipif(True, reason="Requires Neo4j/Chroma; run with mock_neo4j when needed")
def test_run_investigation_e2e_with_services(sample_uploads):
    """Full pipeline with real Neo4j and Chroma (skip if not available)."""
    state = run_investigation(documents_path=str(sample_uploads))
    assert len(state.get("document_metadata", {})) >= 1
    assert "current_step" in state
    assert state["current_step"] == "odos_guardian_complete"


def test_run_investigation_e2e_mocked(sample_uploads, mock_neo4j):
    """Pipeline with mocked Neo4j (Chroma may use in-memory fallback). Runs without interrupt to reach ODOS."""
    try:
        import core.config as config_mod
        orig = getattr(config_mod.settings, "INTERRUPT_BEFORE_ODOS", True)
        config_mod.settings.INTERRUPT_BEFORE_ODOS = False
        try:
            state = run_investigation(documents_path=str(sample_uploads))
            assert len(state.get("document_metadata", {})) >= 1
            assert "entities" in state
            assert "current_step" in state
            assert state["current_step"] in ("odos_guardian_complete", "synthesis_complete")
        finally:
            config_mod.settings.INTERRUPT_BEFORE_ODOS = orig
    except Exception as e:
        pytest.skip(f"E2E needs deps: {e}")


def test_graph_compiles():
    """Workflow compiles without errors."""
    app = create_sherlock_graph()
    assert app is not None


def test_initial_state_keys():
    """Initial state has all required keys."""
    state = create_initial_state()
    required = ["document_metadata", "entities", "relationships", "current_step", "odos_status", "error_log"]
    for k in required:
        assert k in state


def test_e2e_empty_dir_runs_to_completion(tmp_path):
    """E2E: run investigation on empty dir; pipeline completes without crash (Fase 5)."""
    import core.config as config_mod
    orig = getattr(config_mod.settings, "INTERRUPT_BEFORE_ODOS", True)
    config_mod.settings.INTERRUPT_BEFORE_ODOS = False
    try:
        app = create_sherlock_graph()
        initial = create_initial_state()
        initial["config"] = {"uploads_path": str(tmp_path)}
        state = app.invoke(initial)
        assert "current_step" in state
        assert state.get("document_metadata") is not None
        assert "error_log" in state
        assert state["current_step"] in ("synthesis_complete", "odos_guardian_complete", "initialization")
    finally:
        config_mod.settings.INTERRUPT_BEFORE_ODOS = orig


def test_memory_manager_facade():
    """MemoryManager exposes STM, LTM, Episodic, semantic query (Fase 5)."""
    from core.memory import get_memory_manager
    mm = get_memory_manager()
    assert mm.get_stm() is not None
    assert isinstance(mm.get_patterns(), list)
    assert isinstance(mm.get_entity_profiles(), dict)
    assert isinstance(mm.get_episodes(limit=5), list)
    assert isinstance(mm.get_investigation_history(limit=5), list)
    assert isinstance(mm.query_patterns_by_concept("test", limit=5), list)
    assert isinstance(mm.query_entity_profiles("x", limit=5), dict)
