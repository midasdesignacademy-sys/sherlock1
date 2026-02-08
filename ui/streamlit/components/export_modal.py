"""Export modal / buttons (JSON, CSV)."""
import streamlit as st
from typing import Any, List, Dict


def export_buttons(data: List[Dict[str, Any]], base_name: str = "export") -> None:
    if not data:
        return
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Download JSON", data=__import__("json").dumps(data, ensure_ascii=False, indent=2), file_name=f"{base_name}.json", mime="application/json")
    with col2:
        if data and isinstance(data[0], dict):
            keys = list(data[0].keys())
            csv = ",".join(keys) + "\n" + "\n".join(",".join(str(r.get(k, "")) for k in keys) for r in data)
        else:
            csv = ""
        st.download_button("Download CSV", data=csv, file_name=f"{base_name}.csv", mime="text/csv")
