"""
SHERLOCK - Intelligence Synthesis Agent (Agent 9)
Soul: Pattern aggregation → hypotheses (ranked) → narrative → report_summary; leads (lead_id, action, priority, justification).
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger

from core.state import InvestigationState, Hypothesis
from core.config import settings

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def _hypothesis_to_dict(h: Any) -> Dict[str, Any]:
    if hasattr(h, "model_dump"):
        d = h.model_dump()
    elif isinstance(h, dict):
        d = dict(h)
    else:
        d = {"hypothesis_id": getattr(h, "hypothesis_id", ""), "description": getattr(h, "description", ""), "confidence": getattr(h, "confidence", 0)}
    d.setdefault("title", (d.get("description") or "")[:80])
    d.setdefault("status", "under_review")
    return d


def _build_report_summary(state: InvestigationState, hypotheses: List[Any], leads: List[Dict]) -> str:
    """Soul: Executive Summary, Key Findings, Hypotheses, Leads, Timeline, Network (narrative)."""
    parts = []
    doc_count = len(state.get("document_metadata", {}) or {})
    entity_count = len(state.get("entities", {}) or {})
    rel_count = len(state.get("relationships", []) or [])
    timeline = state.get("timeline", []) or []
    patterns = state.get("patterns", []) or []

    parts.append("## Executive Summary")
    parts.append(f"This investigation processed {doc_count} documents, extracting {entity_count} entities and {rel_count} relationships.")
    if timeline:
        parts.append(f"Timeline: {len(timeline)} events reconstructed.")
    parts.append("")

    parts.append("## Key Findings")
    if patterns:
        for p in patterns[:5]:
            desc = p.get("description", getattr(p, "description", "")) if isinstance(p, dict) else getattr(p, "description", "")
            if desc:
                parts.append(f"- {desc[:200]}")
    if not parts[-1].strip().startswith("-"):
        parts.append("- No structured patterns identified; see hypotheses and leads.")
    parts.append("")

    parts.append("## Hypotheses (confidence-ranked)")
    for h in sorted(hypotheses, key=lambda x: -(x.get("confidence", getattr(x, "confidence", 0)) if isinstance(x, dict) else getattr(x, "confidence", 0)))[:10]:
        d = _hypothesis_to_dict(h)
        parts.append(f"- [{d.get('hypothesis_id', '?')}] {d.get('title', d.get('description', ''))[:100]} (confidence: {d.get('confidence', 0):.2f})")
    parts.append("")

    parts.append("## Actionable Leads")
    for L in leads[:10]:
        action = L.get("action", L.get("description", ""))
        priority = L.get("priority", "medium")
        justification = L.get("justification", L.get("rationale", ""))
        parts.append(f"- [{priority}] {action[:120]}" + (f" — {justification[:80]}" if justification else ""))
    parts.append("")

    if timeline:
        parts.append("## Timeline (summary)")
        parts.append(f"{len(timeline)} events; review full timeline for chronology.")
    gm = state.get("graph_metadata", {}) or {}
    if gm.get("node_count") or gm.get("edge_count"):
        parts.append("## Network")
        parts.append(f"Graph: {gm.get('node_count', 0)} nodes, {gm.get('edge_count', gm.get('relationship_count', 0))} edges.")
    return "\n".join(parts)


class IntelligenceSynthesisAgent:
    """Agent 9: Synthesize state into hypotheses, leads, report_summary (Soul); write report files."""

    def process(self, state: InvestigationState) -> InvestigationState:
        logger.info("[Agent 9] Intelligence synthesis...")
        try:
            hypotheses = list(state.get("hypotheses", []))
            leads = list(state.get("leads", []))

            entities = state.get("entities", {}) or {}
            relationships = state.get("relationships", []) or []
            timeline = state.get("timeline", []) or []
            semantic_links = state.get("semantic_links", []) or []
            patterns = state.get("patterns", []) or []

            # Build hypotheses from patterns and centrality (Soul: hypothesis_id, title, description, confidence, supporting_evidence, status)
            centrality = state.get("centrality_scores", {}) or {}
            if not hypotheses and patterns:
                for i, p in enumerate(patterns[:5]):
                    desc = p.get("description", getattr(p, "description", "")) if isinstance(p, dict) else getattr(p, "description", "Pattern")
                    ev = p.get("evidence", getattr(p, "evidence", [])) or p.get("entities_involved", getattr(p, "entities_involved", []))
                    conf = p.get("confidence", getattr(p, "confidence", 0.5)) if isinstance(p, dict) else getattr(p, "confidence", 0.5)
                    hypotheses.append(
                        Hypothesis(
                            hypothesis_id=f"H{i+1}",
                            title=desc[:80] if desc else f"Pattern P{i+1}",
                            description=desc,
                            confidence=float(conf),
                            supporting_evidence=ev if isinstance(ev, list) else [],
                            entities_involved=ev if isinstance(ev, list) else [],
                            doc_ids_supporting=[],
                            next_steps=[],
                            status="under_review",
                        )
                    )
            if centrality and not hypotheses:
                top = sorted(centrality.items(), key=lambda x: -x[1])[:5]
                for i, (eid, score) in enumerate(top):
                    ent = entities.get(eid)
                    name = (ent.get("text") if isinstance(ent, dict) else getattr(ent, "text", eid)) if ent else eid
                    hypotheses.append(
                        Hypothesis(
                            hypothesis_id=f"H{i+1}",
                            title=f"Central entity: {name}"[:80],
                            description=f"Entity '{name}' is central (score {score:.3f})",
                            confidence=min(1.0, score * 2),
                            supporting_evidence=[],
                            entities_involved=[eid],
                            doc_ids_supporting=[],
                            next_steps=["Review documents mentioning this entity"],
                            status="under_review",
                        )
                    )

            # Normalize hypotheses: ensure title and status
            hypotheses = [_hypothesis_to_dict(h) for h in hypotheses]
            state["hypotheses"] = hypotheses

            # Soul leads: [{ lead_id, action, priority, justification }]
            if not leads and timeline:
                leads.append({"lead_id": "L1", "action": "Review chronological events", "priority": "high", "justification": f"{len(timeline)} timeline events"})
            if semantic_links and not any(l.get("link_type") == "semantic" or l.get("type") == "semantic" for l in leads):
                leads.append({"lead_id": "L2", "action": "Review linked documents", "priority": "medium", "justification": f"{len(semantic_links)} semantic links"})
            for i, L in enumerate(leads):
                if not isinstance(L, dict):
                    continue
                L.setdefault("lead_id", L.get("lead_id", f"L{i+1}"))
                L.setdefault("action", L.get("description", L.get("action", "")))
                L.setdefault("priority", L.get("priority", "medium"))
                L.setdefault("justification", L.get("rationale", L.get("justification", "")))
            state["leads"] = leads

            # Soul: report_summary (narrative)
            state["report_summary"] = _build_report_summary(state, hypotheses, leads)

            # Write report files
            reports_dir = settings.REPORTS_DIR
            reports_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = reports_dir / f"report_{ts}.json"
            self._write_json_report(state, json_path)
            if REPORTLAB_AVAILABLE:
                pdf_path = reports_dir / f"report_{ts}.pdf"
                self._write_pdf_report(state, pdf_path)

            state["current_step"] = "synthesis_complete"
            logger.info(f"[Agent 9] Hypotheses: {len(hypotheses)}, Leads: {len(leads)}, report_summary set")
        except Exception as e:
            logger.error(f"[Agent 9] Error: {e}")
            state["error_log"] = state.get("error_log", []) + [f"Synthesis error: {str(e)}"]
        return state

    def _write_json_report(self, state: InvestigationState, path: Path) -> None:
        import json
        hypotheses = state.get("hypotheses", [])
        out = {
            "document_metadata_count": len(state.get("document_metadata", {})),
            "entities_count": len(state.get("entities", {})),
            "relationships_count": len(state.get("relationships", [])),
            "timeline_events": len(state.get("timeline", [])),
            "semantic_links": len(state.get("semantic_links", [])),
            "hypotheses": [h if isinstance(h, dict) else (h.model_dump() if hasattr(h, "model_dump") else h) for h in hypotheses],
            "leads": state.get("leads", []),
            "report_summary": state.get("report_summary"),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        logger.info(f"Report JSON: {path}")

    def _write_pdf_report(self, state: InvestigationState, path: Path) -> None:
        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        y = height - 2 * cm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(2 * cm, y, "SHERLOCK Investigation Report")
        y -= 1.5 * cm
        c.setFont("Helvetica", 10)
        c.drawString(2 * cm, y, f"Documents: {len(state.get('document_metadata', {}))}")
        y -= 0.5 * cm
        c.drawString(2 * cm, y, f"Entities: {len(state.get('entities', {}))}")
        y -= 0.5 * cm
        c.drawString(2 * cm, y, f"Relationships: {len(state.get('relationships', []))}")
        y -= 0.5 * cm
        c.drawString(2 * cm, y, f"Timeline events: {len(state.get('timeline', []))}")
        y -= 1 * cm
        c.drawString(2 * cm, y, "Hypotheses:")
        y -= 0.5 * cm
        for h in state.get("hypotheses", [])[:5]:
            desc = h.description if isinstance(h, dict) else getattr(h, "description", "")
            c.setFont("Helvetica", 9)
            c.drawString(2.5 * cm, y, desc[:80] + ("..." if len(desc) > 80 else ""))
            y -= 0.4 * cm
        c.save()
        logger.info(f"Report PDF: {path}")
