"""
SHERLOCK - Guardian check: delta_e and bias alerts.
"""

from typing import List, Any, Dict
from dataclasses import dataclass

from core.state import InvestigationState
from core.config import settings


@dataclass
class GuardianResult:
    delta_e: float
    bias_alerts: List[str]
    passed: bool


def guardian_check(state: InvestigationState) -> GuardianResult:
    """Compute delta_e from contradictions/semantic_links and hypothesis confidence variance; bias from entity concentration."""
    bias_alerts: List[str] = []
    contradictions = state.get("contradictions") or []
    semantic_links = state.get("semantic_links") or []
    num_links = max(1, len(semantic_links))
    delta_e = min(1.0, len(contradictions) / num_links)

    hypotheses = state.get("hypotheses") or []
    if hypotheses:
        confs = []
        for h in hypotheses:
            c = h.get("confidence", getattr(h, "confidence", 0.5))
            confs.append(c)
        import statistics
        if len(confs) >= 2:
            var = statistics.variance(confs)
            delta_e = max(delta_e, min(1.0, var * 2))
        entity_counts: Dict[str, int] = {}
        for h in hypotheses:
            ents = h.get("entities_involved") if isinstance(h, dict) else getattr(h, "entities_involved", [])
            for eid in ents:
                entity_counts[eid] = entity_counts.get(eid, 0) + 1
        for eid, count in entity_counts.items():
            if count >= 3:
                doc_ids = []
                for h in hypotheses:
                    doc_ids.extend(h.get("doc_ids_supporting") if isinstance(h, dict) else getattr(h, "doc_ids_supporting", []))
                if len(set(doc_ids)) < 2:
                    bias_alerts.append(f"Possible confirmation bias: entity {eid} in {count} hypotheses with few distinct docs")

    threshold = getattr(settings, "PQMS_GUARDIAN_THRESHOLD", 0.05)
    passed = delta_e < threshold
    return GuardianResult(delta_e=delta_e, bias_alerts=bias_alerts, passed=passed)
