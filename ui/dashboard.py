"""
SHERLOCK - Streamlit dashboard (Fase 5).
Upload docs, run investigation, view results, activity feed, and graph.
"""

import sys
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from loguru import logger

from core.config import settings
from core.state import create_initial_state
from core.graph import create_sherlock_graph
from core.graph_enhanced import run_monitored_investigation
from knowledge_graph.visualizer import export_from_state

# Default API URL for real-time events
API_URL = "http://localhost:8001"

st.set_page_config(page_title="SHERLOCK", page_icon="🔍", layout="wide")
st.title("🔍 SHERLOCK Intelligence System")

tab_upload, tab_run, tab_activity, tab_results, tab_graph = st.tabs(["Upload", "Run", "Activity", "Results", "Graph"])

with tab_upload:
    st.subheader("Document upload")
    st.info(f"Uploads directory: `{settings.UPLOADS_DIR}`. You can also copy files there manually.")
    uploaded = st.file_uploader("Choose files", type=["txt", "pdf", "docx", "csv"], accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            path = settings.UPLOADS_DIR / f.name
            path.write_bytes(f.getvalue())
        st.success(f"Saved {len(uploaded)} file(s) to {settings.UPLOADS_DIR}")

with tab_run:
    st.subheader("Run investigation")
    api_url = st.text_input("API URL (for monitored run)", value=st.session_state.get("api_url", API_URL), key="api_url")
    col_run, col_api = st.columns(2)
    with col_run:
        if st.button("Start investigation (local)"):
            with st.spinner("Running pipeline..."):
                try:
                    initial = create_initial_state()
                    initial["config"] = {"uploads_path": str(settings.UPLOADS_DIR)}
                    app = create_sherlock_graph()
                    state = app.invoke(initial)
                    st.session_state["last_state"] = state
                    st.session_state["last_run_ok"] = True
                except Exception as e:
                    st.session_state["last_run_ok"] = False
                    st.session_state["last_error"] = str(e)
                    logger.exception("Run failed")
            if st.session_state.get("last_run_ok"):
                st.success("Investigation complete.")
            else:
                st.error(st.session_state.get("last_error", "Unknown error"))
    with col_api:
        if st.button("Start investigation (via API, monitored)"):
            try:
                import httpx
                r = httpx.post(f"{api_url.rstrip('/')}/investigate", json={"uploads_path": str(settings.UPLOADS_DIR)}, timeout=10)
                r.raise_for_status()
                run_id = r.json().get("run_id")
                st.session_state["last_run_id"] = run_id
                st.success(f"Started. Run ID: {run_id}. Check Activity tab.")
            except Exception as e:
                st.error(f"API error: {e}. Is the API running? (uvicorn api.main:app --port 8001)")

with tab_activity:
    st.subheader("Activity feed (real-time)")
    api_url_act = st.session_state.get("api_url", API_URL)
    if st.button("Refresh activity"):
        try:
            import httpx
            r = httpx.get(f"{api_url_act.rstrip('/')}/events", params={"n": 100}, timeout=5)
            r.raise_for_status()
            data = r.json()
            events = data.get("events", [])
            if events:
                rows = [[e.get("agent"), e.get("step"), e.get("timestamp")] for e in reversed(events)]
                st.dataframe(rows, column_config={0: "Agent", 1: "Step", 2: "Timestamp"}, use_container_width=True)
                st.caption("Auto-refresh: run the API and click Refresh every few seconds, or use GET /events/stream for SSE.")
            else:
                st.info("No events yet. Run an investigation via API (Run tab) to see activity.")
        except Exception as e:
            st.warning(f"Could not fetch events: {e}. Start the API: uvicorn api.main:app --port 8001")
    if st.session_state.get("last_run_id"):
        run_id = st.session_state["last_run_id"]
        if st.button("Check run status"):
            try:
                import httpx
                r = httpx.get(f"{api_url_act.rstrip('/')}/runs/{run_id}", params={"full": 1}, timeout=10)
                data = r.json()
                st.write("Status:", data.get("status"))
                if data.get("status") == "completed":
                    full_state = data.get("state") or data.get("state_full")
                    if full_state:
                        st.session_state["last_state"] = full_state
                    st.success("Run completed. See Results tab.")
            except Exception as e:
                st.error(str(e))

with tab_results:
    st.subheader("Results summary")
    state = st.session_state.get("last_state")
    if not state:
        st.warning("Run an investigation first.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Documents", state.get("document_metadata_count") or len(state.get("document_metadata", {})))
        with col2:
            st.metric("Entities", state.get("entities_count") or len(state.get("entities", {})))
        with col3:
            st.metric("Relationships", state.get("relationships_count") or len(state.get("relationships", [])))
        with col4:
            st.metric("ODOS", state.get("odos_status", "—"))
        st.metric("Timeline events", len(state.get("timeline", [])))
        st.metric("Semantic links", len(state.get("semantic_links", [])))
        if state.get("report_summary"):
            st.subheader("Report summary (narrative)")
            st.markdown(state["report_summary"])
        if state.get("hypotheses"):
            st.subheader("Hypotheses")
            for h in state["hypotheses"]:
                d = h if isinstance(h, dict) else {}
                title = d.get("title") or d.get("description", getattr(h, "description", ""))
                conf = d.get("confidence", getattr(h, "confidence", 0))
                st.write(f"- **{title[:120]}** (confidence: {conf:.2f})")
        if state.get("leads"):
            st.subheader("Leads")
            for lead in state["leads"]:
                if isinstance(lead, dict):
                    st.write(f"- [{lead.get('priority', '')}] {lead.get('action', '')} — {lead.get('justification', '')}")
                else:
                    st.write(lead)
        if state.get("compliance_report"):
            with st.expander("ODOS compliance report"):
                st.json(state["compliance_report"])

with tab_graph:
    st.subheader("Knowledge graph")
    state = st.session_state.get("last_state")
    if not state:
        st.warning("Run an investigation first.")
    else:
        if st.button("Export graph to HTML"):
            path = export_from_state(state)
            if path:
                st.success(f"Saved to {path}")
                with open(path, "r", encoding="utf-8") as f:
                    st.download_button("Download HTML", f.read(), file_name="knowledge_graph.html", mime="text/html")
        st.info("Open Neo4j Browser at http://localhost:7474 for full graph exploration.")
