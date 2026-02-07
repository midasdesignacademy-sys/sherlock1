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

    def emit(self, agent: str, step: str, **kwargs: Any) -> None:
        """Append an event: agent name, step (start/end), optional payload."""
        event: Dict[str, Any] = {
            "agent": agent,
            "step": step,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": dict(kwargs) if kwargs else {},
        }
        with self._events_lock:
            self._events.append(event)

    def get_recent(self, n: int = 50) -> List[Dict[str, Any]]:
        """Return the last n events (newest last)."""
        with self._events_lock:
            return list(self._events)[-n:]

    def clear(self) -> None:
        """Clear all events."""
        with self._events_lock:
            self._events.clear()
