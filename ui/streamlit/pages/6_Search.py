"""Search: hybrid search with document title and snippet."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

inv_id = st.session_state.get("investigation_id")
base = st.session_state.get("api_url", "http://localhost:8001").rstrip("/")

st.title("Search")
if not inv_id:
    st.warning("Select an investigation in the sidebar to search over its data. Without one, results may be empty or limited.")

query = st.text_input("Query", key="search_q", placeholder="Enter search terms")
if st.button("Search", key="search_btn"):
    if not query or not query.strip():
        st.warning("Enter a query.")
    else:
        try:
            with st.spinner("Searching..."):
                import httpx
                body = {"query": query.strip(), "n_results": 15}
                if inv_id:
                    body["investigation_id"] = inv_id
                r = httpx.post(f"{base}/search", json=body, timeout=15)
                d = r.json()
                results = d.get("results", [])
                err = d.get("error")
            if err:
                st.warning(err)
            elif not results:
                st.info("No results.")
            else:
                for hit in results:
                    doc_id = hit.get("document_id", hit.get("entity_id", ""))
                    score = hit.get("combined_score", hit.get("vector_score", 0)) or 0
                    snippet = hit.get("snippet", "")
                    st.markdown(f"**{doc_id}** — score: {score:.3f}")
                    if snippet:
                        st.caption(snippet)
                    st.divider()
        except Exception as e:
            st.error(str(e))
