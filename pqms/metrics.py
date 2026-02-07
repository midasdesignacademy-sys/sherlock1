"""
SHERLOCK - Fidelity and RCF metrics (evidence-based).
"""

from typing import List, Any
from core.state import InvestigationState


def compute_fidelity(state: InvestigationState) -> float:
    """Weighted average confidence of entities used in hypotheses; or 1 - rate of non-decrypted segments."""
    hypotheses = state.get("hypotheses") or []
    entities = state.get("entities", {}) or {}
    if not hypotheses:
        encrypted = state.get("encrypted_segments") or []
        decrypted = state.get("decrypted_content") or {}
        if encrypted:
            return len(decrypted) / len(encrypted) if encrypted else 1.0
        return 0.99

    entity_ids_in_hypotheses = set()
    for h in hypotheses:
        entity_ids_in_hypotheses.update(
            h.get("entities_involved") if isinstance(h, dict) else getattr(h, "entities_involved", [])
        )
    confs = []
    for eid in entity_ids_in_hypotheses:
        e = entities.get(eid)
        if e:
            c = e.get("confidence", getattr(e, "confidence", 0.9))
            confs.append(c)
    return sum(confs) / len(confs) if confs else 0.99


def compute_rcf(state: InvestigationState) -> float:
    """Reasoning coherence: hypotheses do not contradict (same entity, opposite claims). Simple heuristic."""
    hypotheses = state.get("hypotheses") or []
    if len(hypotheses) < 2:
        return 0.95
    contradictions = state.get("contradictions") or []
    num_links = max(1, len(state.get("semantic_links") or []))
    coherence = 1.0 - min(1.0, len(contradictions) / num_links)
    return max(0.0, min(1.0, coherence))
