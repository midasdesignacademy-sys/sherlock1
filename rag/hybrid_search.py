"""
SHERLOCK - Hybrid search (vector + graph).
Plan: vector search ChromaDB -> entities from docs -> Neo4j expansion -> re-rank (0.6 * vector + 0.4 * centrality).
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from rag.vector_store import get_chroma_client, get_or_create_collection, query_similar
from rag.embeddings import get_embedding_model


def _similarity_from_distance(distance: Optional[float]) -> float:
    if distance is None:
        return 0.0
    return max(0.0, 1.0 - distance)


def hybrid_search(
    query: str,
    state: Dict[str, Any],
    n_results: int = 10,
    vector_weight: float = 0.6,
    centrality_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid search: vector search on ChromaDB, then expand via Neo4j from entities in those docs, re-rank.
    Returns list of { "entity_id", "entity_text", "combined_score", "vector_score", "centrality", "source" }.
    """
    try:
        model = get_embedding_model()
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        vector_hits = query_similar(query, n_results=n_results * 2, collection=collection, model=model)
    except Exception as e:
        logger.warning(f"Hybrid search vector step failed: {e}")
        return []

    doc_ids_from_vector = []
    doc_scores: Dict[str, float] = {}
    for hit in vector_hits:
        meta = hit.get("metadata", {}) or {}
        doc_id = meta.get("doc_id")
        if doc_id:
            doc_ids_from_vector.append(doc_id)
            dist = hit.get("distance")
            sim = _similarity_from_distance(dist)
            doc_scores[doc_id] = max(doc_scores.get(doc_id, 0), sim)

    entities = state.get("entities", {}) or {}
    centrality_scores = state.get("centrality_scores", {}) or state.get("graph_metadata", {}).get("centrality", {})
    entity_ids_from_docs: List[str] = []
    if isinstance(entities, dict):
        for eid, ent in entities.items():
            docs = ent.get("documents", []) if isinstance(ent, dict) else getattr(ent, "documents", [])
            if any(d in doc_ids_from_vector for d in docs):
                entity_ids_from_docs.append(eid)

    expanded: Dict[str, Dict[str, Any]] = {}
    for eid in entity_ids_from_docs:
        ent = entities.get(eid) if isinstance(entities, dict) else None
        text = ent.get("text", eid) if isinstance(ent, dict) else getattr(ent, "text", eid)
        vec_score = max(doc_scores.get(d, 0) for d in (ent.get("documents", []) if isinstance(ent, dict) else [])) if doc_ids_from_vector else 0.5
        cent = centrality_scores.get(eid, 0.0) if isinstance(centrality_scores, dict) else 0.0
        combined = vector_weight * vec_score + centrality_weight * cent
        expanded[eid] = {
            "entity_id": eid,
            "entity_text": text,
            "combined_score": combined,
            "vector_score": vec_score,
            "centrality": cent,
            "source": "vector",
        }

    try:
        from knowledge_graph.neo4j_client import Neo4jClient
        neo = Neo4jClient()
        neo.connect()
        neighbors = neo.get_neighbors(entity_ids_from_docs[:20], limit_per_entity=5)
        neo.close()
        for n in neighbors:
            eid = n.get("entity_id")
            if not eid or eid in expanded:
                continue
            cent = centrality_scores.get(eid, 0.0) if isinstance(centrality_scores, dict) else 0.0
            expanded[eid] = {
                "entity_id": eid,
                "entity_text": n.get("text", eid),
                "combined_score": centrality_weight * cent,
                "vector_score": 0.0,
                "centrality": cent,
                "source": "graph",
            }
    except Exception as e:
        logger.debug(f"Hybrid search graph expansion skipped: {e}")

    sorted_results = sorted(expanded.values(), key=lambda x: x["combined_score"], reverse=True)[:n_results]
    return sorted_results
