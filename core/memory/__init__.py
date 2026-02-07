"""
SHERLOCK - Multi-layer memory (STM, LTM, Episodic, Semantic). Fase 5: MemoryManager.
"""

from core.memory.short_term import ShortTermMemory, get_stm
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
from core.memory.memory_manager import MemoryManager, get_memory_manager

__all__ = [
    "ShortTermMemory",
    "get_stm",
    "store_pattern",
    "get_patterns",
    "store_entity_profile",
    "get_entity_profiles",
    "append_investigation_history",
    "get_investigation_history",
    "record_episode",
    "get_episodes",
    "consolidate_memories",
    "MemoryManager",
    "get_memory_manager",
]
