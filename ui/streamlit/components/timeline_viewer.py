"""Timeline viewer component."""
import streamlit as st
from typing import Any, List


def render_timeline(timeline: List[Any]) -> None:
    if not timeline:
        st.info(
            "No timeline for this investigation yet. Run the pipeline from the **Dashboard**, "
            "then return here."
        )
        return
    for ev in timeline[:100]:
        if isinstance(ev, dict):
            date = ev.get("date") or ev.get("timestamp") or ev.get("event_id", "")
            desc = ev.get("description", "")
            entities = ev.get("entities_involved", ev.get("entities", [])) or []
            ent_str = ", ".join(entities[:5]) if isinstance(entities, list) else str(entities)[:100]
            st.markdown(f"- **{date}** — {desc}")
            if ent_str:
                st.caption(f"Entities: {ent_str}")
        else:
            st.markdown(f"- {getattr(ev, 'description', str(ev))}")
