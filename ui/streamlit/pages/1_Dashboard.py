"""Dashboard: metrics, activity feed, new investigation."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

API_URL = st.session_state.get("api_url", "http://localhost:8001")
inv_id = st.session_state.get("investigation_id")

with st.sidebar:
    st.session_state["api_url"] = st.text_input("API URL", value=API_URL, key="api_url_dash")
    try:
        import httpx
        r = httpx.get(f"{st.session_state['api_url'].rstrip('/')}/investigations", timeout=5)
        invs = r.json().get("investigations", [])
    except Exception:
        invs = []
    if invs:
        opts = [f"{m.get('name', m.get('id'))} ({m.get('id')})" for m in invs]
        idx = 0
        if st.session_state.get("investigation_id"):
            for i, m in enumerate(invs):
                if m.get("id") == st.session_state["investigation_id"]:
                    idx = i
                    break
        sel = st.selectbox("Investigation", opts, index=idx, key="inv_dash")
        if sel:
            st.session_state["investigation_id"] = invs[opts.index(sel)].get("id")

st.title("Dashboard")
base = st.session_state["api_url"].rstrip("/")

# Metrics from current investigation or placeholder
doc_count = entity_count = hyp_count = 0
odos_status = "—"
if inv_id:
    try:
        with st.spinner("Loading..."):
            import httpx
            r = httpx.get(f"{base}/investigations/{inv_id}", timeout=5)
            d = r.json()
            summary = d.get("summary", {})
            doc_count = summary.get("document_count", 0)
            entity_count = summary.get("entity_count", 0)
            hyp_count = 0
            odos_status = summary.get("odos_status", "—")
            state_r = httpx.get(f"{base}/investigations/{inv_id}/state", timeout=5)
            state_data = state_r.json().get("state", {})
            if state_data:
                hyp_count = len(state_data.get("hypotheses", []))
    except Exception:
        pass

c1, c2, c3, c4 = st.columns(4)
c1.metric("Documents", doc_count)
c2.metric("Entities", entity_count)
c3.metric("Hypotheses", hyp_count)
c4.metric("ODOS", odos_status)

# Activity feed
st.subheader("Activity feed")
try:
    with st.spinner("Loading..."):
        import httpx
        r = httpx.get(f"{base}/events", params={"n": 20}, timeout=5)
        events = r.json().get("events", [])
    if events:
        for e in reversed(events[-15:]):
            st.caption(f"{e.get('timestamp', '')} — {e.get('agent', '')}: {e.get('step', '')}")
    else:
        st.info("No events. Run an investigation.")
except Exception as e:
    st.warning(f"Could not load events: {e}")

# New investigation: 1) Create 2) Upload files 3) Run
st.subheader("New investigation")

# Step 1: Create investigation
st.markdown("**1. Create investigation**")
name = st.text_input("Name (optional)", key="new_inv_name", placeholder="e.g. Case 2024-01")
if st.button("Create investigation", key="btn_create_inv"):
    try:
        import httpx
        r = httpx.post(f"{base}/investigations", json={"name": name.strip() or None}, timeout=10)
        r.raise_for_status()
        d = r.json()
        st.session_state["investigation_id"] = d.get("investigation_id")
        st.success(f"Created: {d.get('investigation_id')}. Now add files below.")
        st.rerun()
    except Exception as e:
        st.error(str(e))

# Step 2: Upload files (when an investigation is selected)
inv_id = st.session_state.get("investigation_id")
if inv_id:
    st.markdown("**2. Send files**")
    accept_extensions = ["pdf", "docx", "doc", "txt", "xlsx", "xls", "csv", "json", "xml", "html", "eml", "msg", "png", "jpg", "jpeg"]
    uploaded = st.file_uploader("Choose one or more files", accept_multiple_files=True, type=accept_extensions, key="dashboard_uploads")
    global_description = st.text_area("Description (applied to all)", key="upload_global_desc", placeholder="Optional description for this batch")
    with st.expander("Per-file descriptions (optional)"):
        per_file_desc = {}
        for u in (uploaded or []):
            per_file_desc[u.name] = st.text_input(f"Description for {u.name}", key=f"desc_{u.name}", placeholder="Optional")
    if st.button("Upload files", key="btn_upload"):
        if not uploaded:
            st.warning("Select at least one file.")
        else:
            try:
                import httpx
                import json
                files = [("files", (u.name, u.getvalue())) for u in uploaded]
                data = {}
                if global_description and global_description.strip():
                    data["description"] = global_description.strip()
                if any(per_file_desc.get(u.name) for u in uploaded):
                    data["descriptions"] = json.dumps({u.name: (per_file_desc.get(u.name) or "").strip() for u in uploaded})
                r = httpx.post(f"{base}/investigations/{inv_id}/uploads", files=files, data=data, timeout=60)
                r.raise_for_status()
                d = r.json()
                st.success(f"Uploaded {d.get('total', 0)} file(s). You can run the analysis below.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    # List already uploaded files
    try:
        r = httpx.get(f"{base}/investigations/{inv_id}/files", timeout=5)
        if r.status_code == 200:
            fd = r.json()
            flist = fd.get("files", [])
            if flist:
                st.caption("Files in this investigation:")
                for f in flist:
                    st.caption(f" — {f.get('name')} ({f.get('size', 0)} bytes)" + (f" — {f.get('description', '')[:50]}..." if f.get('description') else ""))
    except Exception:
        pass

    # Step 3: Run pipeline
    st.markdown("**3. Run analysis**")
    if st.button("Run analysis", key="btn_run"):
        try:
            import httpx
            r = httpx.post(f"{base}/investigations/{inv_id}/run", timeout=10)
            if r.status_code == 400:
                st.warning("Add files first, then run.")
            else:
                r.raise_for_status()
                st.success("Analysis started. Check the activity feed and refresh when done.")
                st.rerun()
        except Exception as e:
            st.error(str(e))
else:
    st.info("Create an investigation above or select one from the sidebar.")
