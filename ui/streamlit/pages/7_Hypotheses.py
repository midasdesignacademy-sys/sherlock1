"""Hypotheses list with evidence and confidence filter."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

inv_id = st.session_state.get("investigation_id")
base = st.session_state.get("api_url", "http://localhost:8001").rstrip("/")
st.title("Hypotheses")

if not inv_id:
    st.warning("Select an investigation in the sidebar or create one from the **Dashboard**.")
    st.stop()

try:
    with st.spinner("Loading..."):
        import httpx
        r = httpx.get(f"{base}/investigations/{inv_id}/state", timeout=10)
        if r.status_code != 200:
            st.error("Could not load investigation state.")
            st.stop()
        state = r.json().get("state", {})
except Exception as e:
    st.error(str(e))
    st.stop()

hyps = state.get("hypotheses", []) or []
if not hyps:
    st.info(
        "No hypotheses for this investigation yet. Add files and **Run analysis** on the **Dashboard**, "
        "then return here."
    )
    st.stop()

min_conf = st.slider("Min confidence", 0.0, 1.0, 0.0, 0.05, key="hyp_min_conf")
filtered = [h for h in hyps if isinstance(h, dict) and (h.get("confidence", 0) or 0) >= min_conf]

for i, h in enumerate(filtered):
    d = h if isinstance(h, dict) else {}
    title = d.get("title", d.get("description", ""))[:120] or f"Hypothesis {i+1}"
    desc = d.get("description", "")
    conf = d.get("confidence", 0)
    evidence = d.get("supporting_evidence", d.get("evidence", [])) or []
    status = d.get("status", "")
    with st.container():
        st.markdown(f"**{title}**")
        st.caption(f"Confidence: {conf:.2f}" + (f" — Status: {status}" if status else ""))
        if desc and desc != title:
            st.write(desc)
        if evidence:
            with st.expander("Evidence"):
                for e in (evidence if isinstance(evidence, list) else [evidence])[:20]:
                    st.caption(str(e)[:300])
        st.divider()
