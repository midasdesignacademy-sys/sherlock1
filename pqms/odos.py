"""
SHERLOCK - ODOS validation (rules-based).
"""

from typing import List, Any, Dict
from dataclasses import dataclass
from enum import Enum


class OdosStatus(str, Enum):
    """Soul: VALID (proceed), NEEDS_REVIEW (human review), BLOCKED (critical)."""
    VALID = "VALID"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


@dataclass
class OdosViolation:
    type: str
    count: int
    severity: str  # low, medium, high, critical


@dataclass
class OdosResult:
    status: OdosStatus
    message: str = ""
    violations: List[OdosViolation] = None

    def __post_init__(self):
        if self.violations is None:
            self.violations = []


def validate_odos(findings: List[Any], state: Dict[str, Any]) -> OdosResult:
    """Validate ethical constraints: evidence backing, PII, empty findings. Returns violations (Soul)."""
    violations: List[OdosViolation] = []
    compliance = state.get("compliance_report") or {}

    if compliance.get("pii_critical"):
        violations.append(OdosViolation(type="pii_exposure", count=1, severity="critical"))
        return OdosResult(status=OdosStatus.BLOCKED, message="PII critical: review required", violations=violations)

    if not findings:
        return OdosResult(status=OdosStatus.VALID, message="No findings to validate", violations=[])

    relationships = state.get("relationships") or []
    evidence_doc_ids = set()
    for r in relationships:
        for doc_id in (r.get("evidence_doc_ids") if isinstance(r, dict) else getattr(r, "evidence_doc_ids", [])):
            evidence_doc_ids.add(doc_id)

    entity_to_docs: Dict[str, set] = {}
    for r in relationships:
        src = r.get("source_entity_id") if isinstance(r, dict) else getattr(r, "source_entity_id", None)
        tgt = r.get("target_entity_id") if isinstance(r, dict) else getattr(r, "target_entity_id", None)
        for eid in (src, tgt):
            if eid:
                if eid not in entity_to_docs:
                    entity_to_docs[eid] = set()
                for doc_id in (r.get("evidence_doc_ids") if isinstance(r, dict) else getattr(r, "evidence_doc_ids", [])):
                    entity_to_docs[eid].add(doc_id)

    for f in findings:
        if not f:
            continue
        entities_involved = f.get("entities_involved") if isinstance(f, dict) else getattr(f, "entities_involved", [])
        doc_ids_supporting = f.get("doc_ids_supporting") if isinstance(f, dict) else getattr(f, "doc_ids_supporting", [])
        for eid in entities_involved:
            if eid and not entity_to_docs.get(eid) and not doc_ids_supporting:
                violations.append(OdosViolation(type="unbacked_entity", count=1, severity="medium"))
                return OdosResult(
                    status=OdosStatus.NEEDS_REVIEW,
                    message=f"Entity {eid} in findings without evidence in relationships or doc_ids",
                    violations=violations,
                )

    return OdosResult(status=OdosStatus.VALID, message="ODOS validation passed", violations=violations)
