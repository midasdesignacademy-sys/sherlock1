"""
SHERLOCK - Long-Term Memory (LTM).
Soul: patterns, entity_profiles, extraction_method; persist in data/knowledge_base/.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock

from core.config import settings

_LOCK = Lock()
_PATTERNS_FILE = "patterns.json"
_ENTITY_PROFILES_FILE = "entity_profiles.json"
_INVESTIGATION_HISTORY_FILE = "investigation_history.json"


def _kb_path(name: str) -> Path:
    settings.KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    return settings.KNOWLEDGE_BASE_DIR / name


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with _LOCK:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def store_pattern(
    pattern_type: str,
    description: str,
    evidence: List[str],
    confidence: float,
    investigation_id: Optional[str] = None,
) -> None:
    """Store a learned pattern in LTM (Soul)."""
    path = _kb_path(_PATTERNS_FILE)
    data = _load_json(path, [])
    entry = {
        "pattern_type": pattern_type,
        "description": description,
        "evidence": evidence,
        "confidence": confidence,
        "investigation_id": investigation_id,
    }
    data.append(entry)
    _save_json(path, data[-500:])  # keep last 500


def get_patterns(pattern_type: Optional[str] = None, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
    """Retrieve patterns from LTM, optionally filtered."""
    path = _kb_path(_PATTERNS_FILE)
    data = _load_json(path, [])
    if pattern_type:
        data = [p for p in data if p.get("pattern_type") == pattern_type]
    if min_confidence > 0:
        data = [p for p in data if p.get("confidence", 0) >= min_confidence]
    return data


def store_entity_profile(entity_text: str, profile: Dict[str, Any], investigation_id: Optional[str] = None) -> None:
    """Store or update entity profile in LTM."""
    path = _kb_path(_ENTITY_PROFILES_FILE)
    data = _load_json(path, {})
    key = (entity_text or "").strip() or "_unknown"
    if key not in data:
        data[key] = []
    data[key].append({
        "profile": profile,
        "investigation_id": investigation_id,
    })
    data[key] = data[key][-20:]
    _save_json(path, data)


def get_entity_profiles(entity_text: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieve entity profiles from LTM."""
    path = _kb_path(_ENTITY_PROFILES_FILE)
    data = _load_json(path, {})
    if entity_text is not None:
        key = (entity_text or "").strip() or "_unknown"
        return {key: data.get(key, [])}
    return data


def store_extraction_method(source: str, method: str, confidence: float) -> None:
    """Store preferred extraction method by source (e.g. file type/producer)."""
    path = _kb_path("extraction_methods.json")
    data = _load_json(path, [])
    data.append({"source": source, "method": method, "confidence": confidence})
    _save_json(path, data[-200:])


def append_investigation_history(investigation_id: str, summary: Dict[str, Any]) -> None:
    """Append investigation summary to history."""
    path = _kb_path(_INVESTIGATION_HISTORY_FILE)
    data = _load_json(path, [])
    data.append({"investigation_id": investigation_id, **summary})
    _save_json(path, data[-100:])


def get_investigation_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Return last N investigation summaries from LTM."""
    path = _kb_path(_INVESTIGATION_HISTORY_FILE)
    data = _load_json(path, [])
    return list(data[-limit:])
