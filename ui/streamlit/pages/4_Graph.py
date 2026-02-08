"""Knowledge graph viewer (Pyvis)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from ui.streamlit.components.graph_viewer import render_graph_from_state

inv_id = st.session_state.get("investigation_id")
base = st.session_state.get("api_url", "http://localhost:8001").rstrip("/")

st.title("Knowledge Graph")
if not inv_id:
    st.warning("Select an investigation in the sidebar or create one from the **Dashboard**.")
    st.stop()
try:
    with st.spinner("Loading..."):
        import httpx
        r = httpx.get(f"{base}/investigations/{inv_id}/state", timeout=10)
        state = r.json().get("state", {})
    render_graph_from_state(state)
except Exception as e:
    st.error(str(e))
