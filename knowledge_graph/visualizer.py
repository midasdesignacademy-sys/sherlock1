"""
SHERLOCK - Export Knowledge Graph to interactive HTML (pyvis).
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

from core.config import settings


def _to_dict(obj) -> dict:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj if isinstance(obj, dict) else {}


def build_network_html(
    entities: Dict[str, Any],
    relationships: List[Any],
    output_path: Optional[Path] = None,
    max_nodes: int = 200,
    max_edges: int = 500,
) -> str:
    """Build pyvis Network and save to HTML. Returns path or HTML string."""
    try:
        from pyvis.network import Network
    except ImportError:
        logger.warning("pyvis not installed; skipping graph visualization")
        return ""

    net = Network(height="600px", width="100%", directed=True)
    added = set()
    for eid, ent in list(entities.items())[:max_nodes]:
        d = _to_dict(ent)
        label = d.get("text", eid)[:30]
        etype = d.get("entity_type", "ENTITY")
        net.add_node(eid, label=label, title=f"{etype}: {label}", group=etype)
        added.add(eid)

    for r in relationships[:max_edges]:
        src = r.source_entity_id if hasattr(r, "source_entity_id") else r.get("source_entity_id")
        tgt = r.target_entity_id if hasattr(r, "target_entity_id") else r.get("target_entity_id")
        if src in added and tgt in added:
            net.add_edge(src, tgt)

    html = net.generate_html()
    if output_path is None:
        output_path = settings.GRAPHS_DIR / "knowledge_graph.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"Graph HTML: {output_path}")
    return str(output_path)


def export_from_state(state: Dict[str, Any], filename: str = "knowledge_graph.html") -> str:
    """Export graph from investigation state to HTML."""
    entities = state.get("entities", {}) or {}
    relationships = state.get("relationships", []) or []
    path = settings.GRAPHS_DIR / filename
    return build_network_html(entities, relationships, output_path=path) or ""
