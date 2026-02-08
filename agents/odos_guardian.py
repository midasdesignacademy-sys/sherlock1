"""
SHERLOCK - ODOS Guardian Agent (Agent 10)
Soul: Validates PQMS/ODOS; outputs odos_status, odos_violations, fidelity, rcf, guardian_delta_e, compliance_report.
Decision: ΔE < 0.05 AND Fidelity > 0.99 → VALID; ΔE < 0.1 AND Fidelity > 0.95 → NEEDS_REVIEW; else → BLOCKED.
"""

from loguru import logger

from core.state import InvestigationState
from core.config import settings
from pqms.odos import validate_odos, OdosStatus, OdosViolation
from pqms.guardian import guardian_check
from pqms.metrics import compute_fidelity, compute_rcf

MAX_DELTA_E_VALID = 0.05
MIN_FIDELITY_VALID = 0.99
MAX_DELTA_E_REVIEW = 0.1
MIN_FIDELITY_REVIEW = 0.95
MIN_RCF = 0.95


def process(state: InvestigationState) -> InvestigationState:
    """Agent 10: ODOS + Guardian + Fidelity/RCF; set odos_violations, guardian_delta_e, compliance_report (Soul)."""
    logger.info("[Agent 10] ODOS Guardian...")
    try:
        findings = []
        if state.get("hypotheses"):
            findings.extend(state["hypotheses"])
        if state.get("leads"):
            findings.extend(state["leads"])

        odos_result = validate_odos(findings, state)
        state["odos_violations"] = [
            {"type": v.type, "count": v.count, "severity": v.severity}
            for v in (odos_result.violations or [])
        ]

        guardian_result = guardian_check(state)
        state["delta_e"] = guardian_result.delta_e
        state["guardian_delta_e"] = guardian_result.delta_e

        fidelity = compute_fidelity(state)
        rcf = compute_rcf(state)
        state["fidelity"] = fidelity
        state["rcf"] = rcf

        cr = state.get("compliance_report") or {}
        cr["fidelity"] = fidelity
        cr["rcf"] = rcf
        if guardian_result.bias_alerts:
            cr["bias_alerts"] = guardian_result.bias_alerts

        # Soul decision: ODOS BLOCKED overrides metrics; else derive from ΔE and Fidelity
        if odos_result.status == OdosStatus.BLOCKED:
            final_status = OdosStatus.BLOCKED.value
            cr["overall_status"] = "BLOCKED"
            cr["recommendations"] = ["Resolve critical ODOS violations (e.g. PII) before publishing."]
        else:
            if guardian_result.delta_e < MAX_DELTA_E_VALID and fidelity >= MIN_FIDELITY_VALID and rcf >= MIN_RCF:
                final_status = OdosStatus.VALID.value
                cr["overall_status"] = "VALID"
                cr["recommendations"] = []
            elif guardian_result.delta_e < MAX_DELTA_E_REVIEW and fidelity >= MIN_FIDELITY_REVIEW:
                final_status = OdosStatus.NEEDS_REVIEW.value
                cr["overall_status"] = "NEEDS_REVIEW"
                cr["recommendations"] = ["Human review recommended: delta_e or fidelity near threshold."]
            else:
                final_status = OdosStatus.BLOCKED.value
                cr["overall_status"] = "BLOCKED"
                cr["recommendations"] = [
                    f"Delta-E {guardian_result.delta_e:.3f} or fidelity {fidelity:.3f} below threshold.",
                    "Improve evidence backing or reduce contradictions before publishing.",
                ]
            if odos_result.status == OdosStatus.NEEDS_REVIEW and final_status == OdosStatus.VALID.value:
                final_status = OdosStatus.NEEDS_REVIEW.value
                cr["overall_status"] = "NEEDS_REVIEW"
                cr["recommendations"] = [odos_result.message] + (cr.get("recommendations") or [])

        state["odos_status"] = final_status
        state["compliance_report"] = cr

        # Optional LLM narrative when GEMINI_API_KEY is set
        try:
            from core.llm import get_llm
            from langchain_core.messages import HumanMessage
            llm = get_llm()
            if llm is not None:
                violations_summary = "; ".join(
                    f"{v.get('type', '')}({v.get('count', 0)})" for v in (state.get("odos_violations") or [])
                ) or "none"
                prompt = (
                    "Em 2-3 frases, resume o resultado da verificação ODOS: "
                    f"violações={violations_summary}, fidelity={fidelity:.2f}, rcf={rcf:.2f}, "
                    f"delta_e={guardian_result.delta_e:.3f}, status={cr.get('overall_status', '')}. "
                    "Linguagem neutra e executiva."
                )
                msg = llm.invoke([HumanMessage(content=prompt[:4000])])
                if getattr(msg, "content", None):
                    cr["narrative"] = msg.content.strip()
        except Exception as e:
            logger.warning(f"ODOS Guardian LLM narrative skipped: {e}")

        state["current_step"] = "odos_guardian_complete"
        logger.info(
            f"[Agent 10] ODOS={final_status}, guardian_delta_e={guardian_result.delta_e:.3f}, "
            f"fidelity={fidelity:.3f}, rcf={rcf:.3f}"
        )
    except Exception as e:
        logger.error(f"[Agent 10] Error: {e}")
        state["error_log"] = state.get("error_log", []) + [f"ODOS Guardian error: {str(e)}"]
        state["odos_status"] = OdosStatus.NEEDS_REVIEW.value
        state["odos_violations"] = state.get("odos_violations", [])
        state["delta_e"] = 0.1
        state["guardian_delta_e"] = 0.1
        state["fidelity"] = 0.0
        state["rcf"] = 0.0
        state["compliance_report"] = state.get("compliance_report") or {}
        state["compliance_report"]["overall_status"] = "NEEDS_REVIEW"
        state["compliance_report"]["recommendations"] = [str(e)]
    return state
