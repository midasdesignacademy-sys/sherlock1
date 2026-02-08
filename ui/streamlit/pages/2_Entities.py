"""Entities viewer: table, filters, export JSON/CSV."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from ui.streamlit.components.entity_table import render_entity_table
from ui.streamlit.components.export_modal import export_buttons

inv_id = st.session_state.get("investigation_id")
base = st.session_state.get("api_url", "http://localhost:8001").rstrip("/")

st.title("Entities")
if not inv_id:
    st.warning("Select an investigation in the sidebar or create one from the **Dashboard**.")
    st.stop()

try:
    with st.spinner("Loading..."):
        import httpx
        r = httpx.get(f"{base}/investigations/{inv_id}/state", timeout=10)
        data = r.json()
        state = data.get("state", {})
except Exception as e:
    st.error(str(e))
    st.stop()

entities = state.get("entities", {}) or {}
if isinstance(entities, dict):
    ent_list = list(entities.values())
else:
    ent_list = []

if not ent_list:
    st.info("No entities for this investigation yet. Add files and **Run analysis** on the **Dashboard**, then return here.")
    st.stop()

with st.sidebar:
    st.subheader("Filters")
    types = list(set(e.get("entity_type", e.get("type", "")) for e in ent_list if isinstance(e, dict)))
    selected_type = st.multiselect("Type", types or ["PERSON", "ORG", "LOC", "DATE", "MONEY"], default=None)
    min_conf = st.slider("Min confidence", 0.0, 1.0, 0.0, 0.05)

filtered = ent_list
if selected_type:
    filtered = [e for e in filtered if isinstance(e, dict) and (e.get("entity_type") or e.get("type")) in selected_type]
if min_conf > 0:
    filtered = [e for e in filtered if isinstance(e, dict) and (e.get("confidence", 0) or 0) >= min_conf]

entities_dict = {str(i): e for i, e in enumerate(filtered)} if filtered else {}
render_entity_table(entities_dict)
export_buttons(filtered, "entities")
