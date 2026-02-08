"""Graph viewer component (Pyvis)."""
import streamlit as st
from pathlib import Path
from typing import Any, Dict, List


def render_graph_from_state(state: Dict[str, Any], height: int = 600) -> None:
    """Render knowledge graph from state (entities + relationships) using Pyvis if available."""
    try:
        from pyvis.network import Network  # noqa: F401
    except ImportError:
        st.info("Install pyvis for graph visualization: `pip install pyvis`")
        return
    entities = state.get("entities", {}) or {}
    relationships = state.get("relationships", []) or []
    if not entities and not relationships:
        st.info("No data for this investigation yet. Run the pipeline or select another investigation. Open **Dashboard** from the sidebar to create or run an investigation.")
        return
    try:
        from knowledge_graph.visualizer import export_from_state
        path = export_from_state(state)
        if path and Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            st.components.v1.html(html, height=height)
        else:
            st.warning("Graph export failed.")
    except Exception as e:
        st.error(f"Graph error: {e}")
