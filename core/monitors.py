"""
SHERLOCK - Activity monitoring for real-time dashboard and API.
"""

import threading
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional


class ActivityMonitor:
    """Singleton activity monitor: thread-safe event buffer for agent steps."""

    _instance: Optional["ActivityMonitor"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ActivityMonitor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_events"):
            return
        self._events: deque = deque(maxlen=500)
        self._events_lock = threading.Lock()

    def emit(self, agent: str, step: str, investigation_id: Optional[str] = None, **kwargs: Any) -> None:
        """Append an event: agent name, step (start/end), optional investigation_id and payload."""
        event: Dict[str, Any] = {
            "agent": agent,
            "step": step,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "investigation_id": investigation_id,
            "payload": dict(kwargs) if kwargs else {},
        }
        with self._events_lock:
            self._events.append(event)

    def get_recent(self, n: int = 50, investigation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return the last n events (newest last). If investigation_id is set, filter by it."""
        with self._events_lock:
            events = list(self._events)[-n:]
        if investigation_id:
            events = [e for e in events if e.get("investigation_id") == investigation_id]
        return events

    def clear(self) -> None:
        """Clear all events."""
        with self._events_lock:
            self._events.clear()
