"""
SHERLOCK - Memory consolidation at end of investigation.
STM (importance > threshold) -> extract patterns -> LTM; append history; clear STM.
"""

from typing import Any, Dict, List
from loguru import logger

from core.memory.short_term import get_stm
from core.memory.long_term import (
    store_pattern,
    append_investigation_history,
    store_entity_profile,
)
from core.memory.episodic import record_episode

STM_IMPORTANCE_THRESHOLD = 0.8


def consolidate_memories(investigation_id: str, state: Dict[str, Any]) -> None:
    """
    At end of investigation: promote important STM to LTM, write history, clear STM.
    """
    stm = get_stm()
    important = stm.retrieve(investigation_id, min_importance=STM_IMPORTANCE_THRESHOLD)
    for item in important:
        content = item.get("content")
        if not content:
            continue
        if isinstance(content, dict):
            if content.get("pattern_type"):
                store_pattern(
                    pattern_type=content.get("pattern_type", "unknown"),
                    description=content.get("description", ""),
                    evidence=content.get("evidence", []),
                    confidence=content.get("confidence", 0.5),
                    investigation_id=investigation_id,
                )
            if content.get("entity"):
                store_entity_profile(
                    content.get("entity", ""),
                    content,
                    investigation_id=investigation_id,
                )

    patterns = state.get("patterns", [])
    for p in patterns[:20]:
        if hasattr(p, "pattern_type"):
            store_pattern(
                pattern_type=getattr(p, "pattern_type", "unknown"),
                description=getattr(p, "description", ""),
                evidence=getattr(p, "evidence", []) or getattr(p, "entities_involved", []),
                confidence=getattr(p, "confidence", 0.5),
                investigation_id=investigation_id,
            )
        elif isinstance(p, dict):
            store_pattern(
                pattern_type=p.get("pattern_type", "unknown"),
                description=p.get("description", ""),
                evidence=p.get("evidence", p.get("entities_involved", [])),
                confidence=p.get("confidence", 0.5),
                investigation_id=investigation_id,
            )

    summary = {
        "document_count": len(state.get("document_metadata", {})),
        "entity_count": len(state.get("entities", {})),
        "relationship_count": len(state.get("relationships", [])),
        "current_step": state.get("current_step"),
        "odos_status": state.get("odos_status"),
    }
    append_investigation_history(investigation_id, summary)
    stm.clear(investigation_id)
    logger.info(f"Consolidated memories for {investigation_id}")
