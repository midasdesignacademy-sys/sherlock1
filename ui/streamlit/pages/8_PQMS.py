"""PQMS / ODOS monitor with narrative and violations list."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

inv_id = st.session_state.get("investigation_id")
base = st.session_state.get("api_url", "http://localhost:8001").rstrip("/")
st.title("PQMS Monitor")

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

# Show narrative first if present (Gemini-generated)
cr = state.get("compliance_report", {}) or {}
narrative = cr.get("narrative", "").strip()
if narrative:
    st.subheader("Summary")
    st.write(narrative)

c1, c2, c3 = st.columns(3)
c1.metric("ODOS Status", state.get("odos_status") or "—")
c2.metric("Fidelity", f"{state.get('fidelity', 0):.2f}" if state.get("fidelity") is not None else "—")
c3.metric("RCF", f"{state.get('rcf', 0):.2f}" if state.get("rcf") is not None else "—")

viol = state.get("odos_violations", []) or []
if viol:
    st.subheader("Violations")
    for v in viol:
        if isinstance(v, dict):
            st.markdown(f"- **{v.get('type', '')}** — count: {v.get('count', 0)}, severity: {v.get('severity', '')}")
        else:
            st.markdown(f"- {v}")

if cr:
    st.subheader("Compliance report (full)")
    st.json(cr)

if not cr and not narrative and not viol:
    st.info(
        "No PQMS data for this investigation yet. Add files and **Run analysis** on the **Dashboard**, "
        "then return here."
    )
