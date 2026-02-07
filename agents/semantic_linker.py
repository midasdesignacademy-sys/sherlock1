"""
SHERLOCK - Semantic Linker Agent (Agent 5)
Soul: docs/agents/agent_5_soul.md
Links documents by semantic similarity; shared_entities, shared_concepts; Soul contract.
"""

import re
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
from loguru import logger

from core.state import InvestigationState, SemanticLink
from core.config import settings
from rag.indexer import index_documents_from_state
from rag.vector_store import get_chroma_client, get_or_create_collection, query_similar
from rag.embeddings import get_embedding_model

# Stopwords (PT/EN) for shared_concepts extraction
_STOP = frozenset(
    "a o e de da do que e em um para com não os as umas dos das pela ao à no na ".split()
    + "the and of to in is for on with as by at be this that it from or ".split()
)
_MIN_CONCEPT_LEN = 4


def _extract_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 10]


def _detect_contradictions_rule_based(
    doc_id_1: str, doc_id_2: str, text1: str, text2: str, entities: Dict
) -> List[Dict[str, Any]]:
    """Rule-based: same entity mentioned with different numbers or dates."""
    out = []
    nums1 = set(re.findall(r"\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+[,.]\d+", text1))
    nums2 = set(re.findall(r"\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+[,.]\d+", text2))
    if nums1 and nums2 and not nums1.intersection(nums2):
        out.append({
            "doc_id_1": doc_id_1, "doc_id_2": doc_id_2,
            "type": "numeric_mismatch", "description": "Different numeric values in linked docs", "evidence": "",
        })
    dates1 = set(re.findall(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}", text1))
    dates2 = set(re.findall(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}", text2))
    if dates1 and dates2 and not dates1.intersection(dates2):
        out.append({
            "doc_id_1": doc_id_1, "doc_id_2": doc_id_2,
            "type": "date_mismatch", "description": "Different dates in linked docs", "evidence": "",
        })
    return out


def _similarity_from_distance(distance: float) -> float:
    """Chroma returns distance (lower = more similar). Convert to similarity in [0,1]."""
    if distance is None:
        return 0.0
    return max(0.0, 1.0 - distance)


def _shared_entities_for_pair(
    doc_i: str, doc_j: str, entities: Any, entity_registry: Dict[str, List[str]]
) -> List[str]:
    """Entity texts that appear in both documents (Soul: shared_entities)."""
    out: List[str] = []
    if not entities:
        return out
    if isinstance(entities, dict):
        for eid, ent in entities.items():
            docs = ent.get("documents", []) if isinstance(ent, dict) else getattr(ent, "documents", [])
            if doc_i in docs and doc_j in docs:
                text = ent.get("text", ent.get("entity_id", "")) if isinstance(ent, dict) else getattr(ent, "text", eid)
                if text and text not in out:
                    out.append(text)
    return out


def _shared_concepts(text1: str, text2: str, top_n: int = 10) -> List[str]:
    """Significant words that appear in both texts (Soul: shared_concepts)."""
    def tokenize(t: str) -> Set[str]:
        words = re.findall(r"[a-zA-ZÀ-ÿ]{3,}", (t or "").lower())
        return {w for w in words if w not in _STOP and len(w) >= _MIN_CONCEPT_LEN}
    w1, w2 = tokenize(text1[:3000]), tokenize(text2[:3000])
    common = list(w1 & w2)[:top_n]
    return common


class SemanticLinkerAgent:
    """Agent 5: Cross-document semantic similarity; fill semantic_links and contradictions."""

    def process(self, state: InvestigationState) -> InvestigationState:
        logger.info("[Agent 5] Semantic linking...")
        try:
            # Ensure index exists
            index_documents_from_state(state)
            extracted = state.get("extracted_text", {})
            doc_ids = list(extracted.keys())
            if len(doc_ids) < 2:
                state["semantic_links"] = state.get("semantic_links", [])
                state["contradictions"] = state.get("contradictions", [])
                state["current_step"] = "semantic_linking_complete"
                return state

            model = get_embedding_model()
            client = get_chroma_client()
            collection = get_or_create_collection(client)

            links: List[SemanticLink] = list(state.get("semantic_links", []))
            seen_pairs: Set[Tuple[str, str]] = set()
            threshold = settings.SEMANTIC_SIMILARITY_THRESHOLD
            max_per_doc = settings.MAX_LINKS_PER_DOCUMENT

            for i, doc_i in enumerate(doc_ids):
                text_i = extracted.get(doc_i, "")[:2000]
                if not text_i:
                    continue
                results = query_similar(
                    text_i,
                    n_results=max_per_doc + len(doc_ids),
                    collection=collection,
                    model=model,
                )
                count_per_doc = 0
                for hit in results:
                    if count_per_doc >= max_per_doc:
                        break
                    meta = hit.get("metadata", {}) or {}
                    doc_j = meta.get("doc_id")
                    if not doc_j or doc_j == doc_i:
                        continue
                    pair = (min(doc_i, doc_j), max(doc_i, doc_j))
                    if pair in seen_pairs:
                        continue
                    dist = hit.get("distance")
                    sim = _similarity_from_distance(dist) if dist is not None else 0.5
                    if sim < threshold:
                        continue
                    shared_ent = _shared_entities_for_pair(
                        doc_i, doc_j,
                        state.get("entities"),
                        state.get("entity_registry", {}),
                    )
                    min_shared = getattr(settings, "MIN_SHARED_ENTITIES", 0)
                    if min_shared > 0 and shared_ent and len(shared_ent) < min_shared:
                        continue
                    seen_pairs.add(pair)
                    count_per_doc += 1
                    text_j = extracted.get(doc_j, "")[:2000]
                    shared_concepts = _shared_concepts(text_i, text_j, top_n=10)
                    rationale = (hit.get("document") or "")[:200]
                    common_entities_legacy = list(set(state.get("entity_registry", {}).keys()) & set(rationale.split()))[:5]
                    link = SemanticLink(
                        doc_id_1=doc_i,
                        doc_id_2=doc_j,
                        similarity_score=round(sim, 4),
                        link_type="semantic",
                        rationale=rationale,
                        common_entities=common_entities_legacy,
                        shared_entities=shared_ent,
                        shared_concepts=shared_concepts,
                    )
                    links.append(link)

            # Contradiction detection (rule-based) for linked pairs
            contradictions = list(state.get("contradictions", []))
            extracted = state.get("extracted_text", {}) or {}
            for link in links:
                d1, d2 = link.doc_id_1, link.doc_id_2
                t1, t2 = extracted.get(d1, ""), extracted.get(d2, "")
                contradictions.extend(_detect_contradictions_rule_based(d1, d2, t1[:5000], t2[:5000], state.get("entities", {})))

            # Narrative threads: cluster doc_ids by links (transitive), title from central doc
            doc_scores: Dict[str, float] = defaultdict(float)
            for link in links:
                doc_scores[link.doc_id_1] += link.similarity_score
                doc_scores[link.doc_id_2] += link.similarity_score
            # Build graph and clusters (union-find style)
            parent: Dict[str, str] = {}
            def find(x: str) -> str:
                if x not in parent:
                    parent[x] = x
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]
            def union(a: str, b: str) -> None:
                parent[find(a)] = find(b)
            for link in links:
                union(link.doc_id_1, link.doc_id_2)
            clusters: Dict[str, List[str]] = defaultdict(list)
            for doc_id in doc_ids:
                clusters[find(doc_id)].append(doc_id)
            narrative_threads = list(state.get("narrative_threads", []))
            for idx, (root, members) in enumerate(clusters.items()):
                if len(members) < 2:
                    continue
                central = max(members, key=lambda d: doc_scores.get(d, 0))
                first_sentence = ""
                text = (extracted.get(central, "") or "").strip()
                for s in _extract_sentences(text):
                    if len(s) > 15:
                        first_sentence = s[:150]
                        break
                narrative_threads.append({
                    "thread_id": f"thread_{idx}",
                    "title": first_sentence or f"Cluster {idx}",
                    "doc_ids": members,
                    "summary": first_sentence,
                })

            state["semantic_links"] = links
            state["contradictions"] = contradictions
            state["narrative_threads"] = narrative_threads
            state["current_step"] = "semantic_linking_complete"
            logger.info(f"[Agent 5] Links: {len(links)}, Contradictions: {len(contradictions)}")
        except Exception as e:
            logger.error(f"[Agent 5] Error: {e}")
            state["error_log"] = state.get("error_log", []) + [f"Semantic linking error: {str(e)}"]
        return state
