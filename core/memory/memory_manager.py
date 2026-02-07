"""
SHERLOCK - Memory Manager (Fase 5).
Single facade for STM, LTM, Episodic, and Semantic memory; orchestrates consolidate_memories.
"""

from typing import Any, Dict, List, Optional

from core.memory.short_term import get_stm, ShortTermMemory
from core.memory.long_term import (
    store_pattern,
    get_patterns,
    store_entity_profile,
    get_entity_profiles,
    append_investigation_history,
    get_investigation_history,
)
from core.memory.episodic import record_episode, get_episodes
from core.memory.consolidate import consolidate_memories


class MemoryManager:
    """
    Facade for all memory layers. Use for agents and API.
    - STM: get_stm().store/retrieve/clear
    - LTM: store_pattern, get_patterns, store_entity_profile, get_entity_profiles, get_investigation_history
    - Episodic: record_episode, get_episodes
    - Semantic: query_patterns_by_concept, query_entity_profiles (LTM + text match)
    - Consolidation: consolidate_memories(investigation_id, state)
    """

    @staticmethod
    def get_stm() -> ShortTermMemory:
        return get_stm()

    # LTM
    @staticmethod
    def store_pattern(
        pattern_type: str,
        description: str,
        evidence: List[str],
        confidence: float,
        investigation_id: Optional[str] = None,
    ) -> None:
        store_pattern(pattern_type, description, evidence, confidence, investigation_id)

    @staticmethod
    def get_patterns(
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        return get_patterns(pattern_type=pattern_type, min_confidence=min_confidence)

    @staticmethod
    def store_entity_profile(
        entity_text: str,
        profile: Dict[str, Any],
        investigation_id: Optional[str] = None,
    ) -> None:
        store_entity_profile(entity_text, profile, investigation_id)

    @staticmethod
    def get_entity_profiles(entity_text: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        return get_entity_profiles(entity_text=entity_text)

    @staticmethod
    def get_investigation_history(limit: int = 50) -> List[Dict[str, Any]]:
        """Last N investigation summaries from LTM."""
        return get_investigation_history(limit=limit)

    # Episodic
    @staticmethod
    def record_episode(
        agent_id: str,
        investigation_id: str,
        action: str,
        reasoning: str = "",
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        record_episode(agent_id, investigation_id, action, reasoning, success, metadata)

    @staticmethod
    def get_episodes(
        investigation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return get_episodes(investigation_id=investigation_id, agent_id=agent_id, limit=limit)

    # Semantic: query LTM by concept/entity text (keyword match)
    @staticmethod
    def query_patterns_by_concept(
        query_text: str,
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Semantic memory: filter LTM patterns by keyword/concept match on description and evidence."""
        if not (query_text or "").strip():
            return get_patterns(pattern_type=pattern_type, min_confidence=min_confidence)[:limit]
        words = set((query_text or "").lower().split())
        all_p = get_patterns(pattern_type=pattern_type, min_confidence=min_confidence)
        scored = []
        for p in all_p:
            desc = (p.get("description") or "").lower()
            evidence = " ".join(p.get("evidence") or []).lower()
            text = f"{desc} {evidence}"
            score = sum(1 for w in words if w in text)
            if score > 0:
                scored.append((score, p))
        scored.sort(key=lambda x: -x[0])
        return [p for _, p in scored[:limit]]

    @staticmethod
    def query_entity_profiles(
        query_text: str,
        limit: int = 20,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Semantic memory: return entity profiles whose key contains query text."""
        all_profiles = get_entity_profiles()
        if not (query_text or "").strip():
            return dict(list(all_profiles.items())[:limit])
        q = (query_text or "").lower()
        out = {}
        for entity_key, profiles in all_profiles.items():
            if q in entity_key.lower():
                out[entity_key] = profiles
                if len(out) >= limit:
                    break
        return out

    @staticmethod
    def consolidate(investigation_id: str, state: Dict[str, Any]) -> None:
        """End-of-investigation: STM → LTM, history, clear STM."""
        consolidate_memories(investigation_id, state)


def get_memory_manager() -> MemoryManager:
    return MemoryManager()
