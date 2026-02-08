"""Entity table component with optional filters."""
import streamlit as st
from typing import Any, Dict, List, Optional


def render_entity_table(entities: Dict[str, Any], columns: Optional[List[str]] = None) -> None:
    if not entities:
        st.info("No entities.")
        return
    rows = []
    for eid, ent in entities.items():
        if isinstance(ent, dict):
            row = {"entity_id": eid, **ent}
        else:
            row = {"entity_id": eid, "text": getattr(ent, "text", ""), "entity_type": getattr(ent, "entity_type", "")}
        rows.append(row)
    st.dataframe(rows, use_container_width=True)
