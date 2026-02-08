"""Documents list from investigation state."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

inv_id = st.session_state.get("investigation_id")
base = st.session_state.get("api_url", "http://localhost:8001").rstrip("/")
st.title("Documents")

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
        data = r.json()
        if data.get("error") == "not_found":
            st.error("Investigation not found.")
            st.stop()
        state = data.get("state", {})
except Exception as e:
    st.error(str(e))
    st.stop()

meta = state.get("document_metadata", {}) or {}
if not meta:
    st.info(
        "No documents for this investigation yet. Add files and **Run analysis** on the **Dashboard**, "
        "then return here to see the processed document list."
    )
    st.stop()

rows = []
for doc_id, m in list(meta.items())[:500]:
    if not isinstance(m, dict):
        continue
    user_desc = (m.get("metadata") or {}).get("user_description", "") or ""
    rows.append({
        "Document": m.get("filename", doc_id),
        "Type": m.get("file_type", ""),
        "Status": m.get("status", ""),
        "Size (bytes)": m.get("size_bytes", 0),
        "Description": user_desc[:200] + ("..." if len(user_desc) > 200 else ""),
        "doc_id": doc_id,
    })
if rows:
    st.dataframe(rows, use_container_width=True, column_config={"doc_id": st.column_config.TextColumn("Doc ID", width="small")})
st.caption(f"Showing up to {len(rows)} documents.")
