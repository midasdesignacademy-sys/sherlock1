"""
SHERLOCK - Streamlit MVP (Arquitetura Frontend v2.0).
Entry: streamlit run ui/streamlit/app.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # ui/streamlit -> ui -> project
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="SHERLOCK", page_icon="🔍", layout="wide")

API_URL = "http://localhost:8001"

if "api_url" not in st.session_state:
    st.session_state["api_url"] = API_URL
if "investigation_id" not in st.session_state:
    st.session_state["investigation_id"] = None

with st.sidebar:
    st.session_state["api_url"] = st.text_input("API URL", value=st.session_state["api_url"], key="api_url_sb")
    api_ok = True
    try:
        import httpx
        r = httpx.get(f"{st.session_state['api_url'].rstrip('/')}/investigations", timeout=5)
        data = r.json()
        invs = data.get("investigations", [])
    except Exception:
        api_ok = False
        invs = []
    if not api_ok:
        st.error("Cannot reach API. Check URL and that the server is running.")
    if invs:
        options = [f"{m.get('name', m.get('id', ''))} ({m.get('id', '')})" for m in invs]
        idx = 0
        if st.session_state.get("investigation_id"):
            for i, m in enumerate(invs):
                if m.get("id") == st.session_state["investigation_id"]:
                    idx = i
                    break
        sel = st.selectbox("Investigation", options, index=idx, key="inv_sel")
        if sel and invs:
            st.session_state["investigation_id"] = invs[options.index(sel)].get("id")
    elif api_ok:
        st.info("No investigations yet. Create one from Dashboard.")

st.title("🔍 SHERLOCK Intelligence System")
st.caption("Select a page from the sidebar (or use the nav above).")
st.markdown("**Dashboard** — metrics, activity, new investigation | **Entities** — table & export | **Search** — full-text | **Graph** — knowledge graph")

st.markdown("---")
st.subheader("Quick start")
st.markdown(
    "1. **Set API URL** in the sidebar and ensure the backend is running (`uvicorn api.main:app --port 8001`).  \n"
    "2. **Create or select an investigation** from the sidebar (create one from the Dashboard).  \n"
    "3. Open **Dashboard** for metrics and activity feed.  \n"
    "4. Use **Entities**, **Graph**, **Search**, and **Timeline** for analysis."
)
