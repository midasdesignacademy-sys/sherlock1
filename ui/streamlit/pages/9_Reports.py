"""Reports: executive summary, hypotheses, leads."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

inv_id = st.session_state.get("investigation_id")
base = st.session_state.get("api_url", "http://localhost:8001").rstrip("/")

st.title("Reports")

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

report_summary = state.get("report_summary")
if report_summary:
    st.subheader("Executive summary")
    st.write(report_summary)
else:
    st.info("No report summary yet. Add files and **Run analysis** on the **Dashboard**, then return here.")

hyps = state.get("hypotheses", []) or []
if hyps:
    st.subheader("Hypotheses")
    st.caption("See the **Hypotheses** page for full detail.")
    for i, h in enumerate(hyps[:10]):
        d = h if isinstance(h, dict) else {}
        title = d.get("title", d.get("description", ""))[:80] or f"Hypothesis {i+1}"
        st.markdown(f"- {title}")

leads = state.get("leads", []) or []
if leads:
    st.subheader("Leads")
    for i, L in enumerate(leads[:15]):
        d = L if isinstance(L, dict) else {}
        action = d.get("action", d.get("description", ""))[:80] or f"Lead {i+1}"
        priority = d.get("priority", "")
        st.markdown(f"- **{action}**" + (f" (priority: {priority})" if priority else ""))

st.divider()
st.caption("Report export (PDF/DOCX) will be available in a later release. Use **Export** on the **Entities** page for JSON/CSV.")
