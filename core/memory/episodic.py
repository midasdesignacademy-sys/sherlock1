"""
SHERLOCK - Episodic Memory.
Soul: record per agent/investigation: action, reasoning, success (JSONL).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from threading import Lock

from core.config import settings

_LOCK = Lock()


def _episodic_dir() -> Path:
    d = settings.KNOWLEDGE_BASE_DIR / "episodic"
    d.mkdir(parents=True, exist_ok=True)
    return d


def record_episode(
    agent_id: str,
    investigation_id: str,
    action: str,
    reasoning: str = "",
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Append one episode (agent decision) to JSONL."""
    d = _episodic_dir()
    file_path = d / "episodes.jsonl"
    entry = {
        "agent_id": agent_id,
        "investigation_id": investigation_id,
        "action": action,
        "reasoning": reasoning[:500] if reasoning else "",
        "success": success,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": metadata or {},
    }
    with _LOCK:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_episodes(
    investigation_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Read recent episodes from JSONL, optionally filtered."""
    file_path = _episodic_dir() / "episodes.jsonl"
    if not file_path.exists():
        return []
    lines = []
    with _LOCK:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    episodes = []
    for line in lines[-limit * 2:]:
        line = line.strip()
        if not line:
            continue
        try:
            ep = json.loads(line)
            if investigation_id and ep.get("investigation_id") != investigation_id:
                continue
            if agent_id and ep.get("agent_id") != agent_id:
                continue
            episodes.append(ep)
        except Exception:
            continue
    return episodes[-limit:]
