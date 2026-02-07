"""
SHERLOCK - Timeline Reconstructor Agent (Agent 6)
Soul: docs/agents/agent_6_soul.md
Extracts events and dates; builds ordered timeline; temporal_anomalies with conflicting_events.
"""

import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

from core.state import InvestigationState, TimelineEvent

try:
    import dateparser
except ImportError:
    dateparser = None

EVENT_TYPE_PATTERNS = [
    (r"\b(?:reunião|meeting|reunir|encontro)\b", "MEETING"),
    (r"\b(?:contrato|contract|acordo|agreement)\b", "CONTRACT"),
    (r"\b(?:pagamento|transferência|transfer|payment|transação)\b", "TRANSACTION"),
    (r"\b(?:viagem|travel|deslocamento)\b", "TRAVEL"),
    (r"\b(?:assinatura|signature|assinado)\b", "SIGNATURE"),
    (r"\b(?:entrega|delivery)\b", "DELIVERY"),
]


def _extract_dates_from_text(text: str) -> List[Tuple[Optional[datetime], int, int, str]]:
    """Return list of (date, start_pos, end_pos, matched_string)."""
    found = []
    patterns = [
        (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
        (r"\d{2}/\d{2}/\d{4}", "%d/%m/%Y"),
        (r"\d{2}-\d{2}-\d{4}", "%d-%m-%Y"),
        (r"\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4}", None),
        (r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}", None),
    ]
    for pat, fmt in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            s = m.group(0)
            try:
                if dateparser:
                    dt = dateparser.parse(s)
                elif fmt:
                    dt = datetime.strptime(s, fmt)
                else:
                    dt = dateparser.parse(s) if dateparser else None
                if dt:
                    found.append((dt, m.start(), m.end(), s))
            except Exception:
                pass
    return found


def _infer_event_type(description: str) -> str:
    desc_lower = (description or "").lower()
    for pat, ev_type in EVENT_TYPE_PATTERNS:
        if re.search(pat, desc_lower, re.IGNORECASE):
            return ev_type
    return "EVENT"


def _entities_in_doc_for_event(description: str, entities: Any, doc_id: str) -> List[str]:
    """Entity texts that appear in this doc and might be in the event description."""
    out: List[str] = []
    if not entities or not description:
        return out
    desc_lower = description.lower()
    if isinstance(entities, dict):
        for eid, ent in entities.items():
            docs = ent.get("documents", []) if isinstance(ent, dict) else getattr(ent, "documents", [])
            if doc_id not in docs:
                continue
            text = ent.get("text", "") if isinstance(ent, dict) else getattr(ent, "text", "")
            if text and text.lower() in desc_lower and text not in out:
                out.append(text)
    return out[:10]


class TimelineReconstructorAgent:
    """Agent 6: Build timeline (date, type, description, entities, documents, confidence); detect anomalies."""

    def process(self, state: InvestigationState) -> InvestigationState:
        logger.info("[Agent 6] Reconstructing timeline...")
        try:
            extracted = state.get("extracted_text", {}) or {}
            entities = state.get("entities", {})
            timeline: List[TimelineEvent] = list(state.get("timeline", []))
            temporal_anomalies: List[Dict[str, Any]] = list(state.get("temporal_anomalies", []))
            event_id = 0

            for doc_id, text in extracted.items():
                if not text:
                    continue
                dates = _extract_dates_from_text(text)
                for dt, start, end, matched in dates:
                    event_id += 1
                    ctx_start = max(0, start - 80)
                    ctx_end = min(len(text), end + 80)
                    desc = text[ctx_start:ctx_end].replace("\n", " ").strip()[:200]
                    ev_type = _infer_event_type(desc)
                    ent_involved = _entities_in_doc_for_event(desc, entities, doc_id)
                    date_iso = dt.strftime("%Y-%m-%d") if dt and hasattr(dt, "strftime") else None
                    timeline.append(
                        TimelineEvent(
                            event_id=f"ev_{event_id}_{uuid.uuid4().hex[:6]}",
                            timestamp=dt,
                            inferred_timestamp=dt,
                            timestamp_confidence=0.85,
                            description=desc,
                            entities_involved=ent_involved,
                            source_doc_ids=[doc_id],
                            date=date_iso,
                            type=ev_type,
                        )
                    )

            def _ts_key(e):
                t = e.timestamp
                if t is None:
                    return ""
                return t.isoformat() if hasattr(t, "isoformat") else str(t)

            timeline.sort(key=_ts_key)

            seen_ts: Dict[str, List[str]] = {}
            for evt in timeline:
                ts = evt.timestamp
                if ts:
                    ts_key = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)
                    if ts_key not in seen_ts:
                        seen_ts[ts_key] = []
                    seen_ts[ts_key].append(evt.event_id)

            for ts_key, evt_ids in seen_ts.items():
                if len(evt_ids) >= 2:
                    temporal_anomalies.append({
                        "type": "possible_duplicate_date",
                        "description": f"Multiple events on same date {ts_key}",
                        "conflicting_events": evt_ids,
                        "timestamp": ts_key,
                    })

            state["timeline"] = timeline
            state["temporal_anomalies"] = temporal_anomalies
            state["current_step"] = "timeline_complete"
            logger.info(f"[Agent 6] Timeline: {len(timeline)} events, Anomalies: {len(temporal_anomalies)}")
        except Exception as e:
            logger.error(f"[Agent 6] Error: {e}")
            state["error_log"] = state.get("error_log", []) + [f"Timeline error: {str(e)}"]
        return state
