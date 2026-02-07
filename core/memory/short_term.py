"""
SHERLOCK - Short-Term Memory (STM).
Soul: during investigation - hashes, progress, failed docs, embeddings cache.
"""

from typing import Any, Dict, List, Optional
from threading import Lock

_store: Dict[str, Dict[str, Any]] = {}
_lock = Lock()


def get_stm() -> "ShortTermMemory":
    return ShortTermMemory()


class ShortTermMemory:
    """
    In-memory store per investigation_id (and optional agent_id).
    Soul: document hashes, processing progress, failed documents, quality scores, embeddings cache.
    """

    def store(
        self,
        investigation_id: str,
        key: str,
        content: Any,
        importance: float = 0.5,
        agent_id: Optional[str] = None,
    ) -> None:
        with _lock:
            k = f"{investigation_id}:{agent_id or 'global'}:{key}"
            _store[k] = {
                "investigation_id": investigation_id,
                "agent_id": agent_id,
                "key": key,
                "content": content,
                "importance": importance,
            }

    def retrieve(
        self,
        investigation_id: str,
        key: Optional[str] = None,
        agent_id: Optional[str] = None,
        min_importance: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        with _lock:
            prefix = f"{investigation_id}:{agent_id or 'global'}:"
            if key:
                prefix += key
                items = [_store[k] for k in _store if k == prefix or k.startswith(prefix + ":")]
            else:
                items = [v for k, v in _store.items() if k.startswith(prefix)]
            if min_importance is not None:
                items = [x for x in items if x.get("importance", 0) >= min_importance]
            return list(items)

    def get_content(
        self,
        investigation_id: str,
        key: str,
        agent_id: Optional[str] = None,
    ) -> Any:
        with _lock:
            k = f"{investigation_id}:{agent_id or 'global'}:{key}"
            entry = _store.get(k)
            return entry["content"] if entry else None

    def clear(self, investigation_id: str, agent_id: Optional[str] = None) -> None:
        with _lock:
            prefix = f"{investigation_id}:"
            if agent_id:
                prefix += f"{agent_id}:"
            to_del = [k for k in _store if k.startswith(prefix)]
            for k in to_del:
                del _store[k]

    def clear_all(self) -> None:
        with _lock:
            _store.clear()
