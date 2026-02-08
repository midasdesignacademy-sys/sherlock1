"""
SHERLOCK - Investigation store (Spec incremental).
Persist investigations: meta.json (id, name, version, batches), state.json (full state).
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import settings

_META_FILE = "meta.json"
_STATE_FILE = "state.json"


def _inv_dir(investigation_id: str) -> Path:
    settings.INVESTIGATIONS_DIR.mkdir(parents=True, exist_ok=True)
    return settings.INVESTIGATIONS_DIR / investigation_id


def create(investigation_id: Optional[str] = None, name: Optional[str] = None) -> str:
    """Create a new investigation; returns investigation_id."""
    inv_id = investigation_id or str(uuid.uuid4())
    d = _inv_dir(inv_id)
    d.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": inv_id,
        "name": name or inv_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "status": "active",
        "version": 1,
        "batches": [],
    }
    (d / _META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return inv_id


def list_all() -> List[Dict[str, Any]]:
    """List all investigations (meta only)."""
    base = settings.INVESTIGATIONS_DIR
    if not base.exists():
        return []
    result = []
    for path in base.iterdir():
        if path.is_dir():
            meta_path = path / _META_FILE
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    result.append(meta)
                except Exception:
                    pass
    result.sort(key=lambda m: m.get("updated_at", ""), reverse=True)
    return result


def get_meta(investigation_id: str) -> Optional[Dict[str, Any]]:
    """Get meta for one investigation."""
    meta_path = _inv_dir(investigation_id) / _META_FILE
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def update_meta(investigation_id: str, updates: Dict[str, Any]) -> None:
    """Update investigation meta with given keys; merge with existing."""
    meta = get_meta(investigation_id)
    if not meta:
        return
    meta.update(updates)
    meta["updated_at"] = datetime.utcnow().isoformat() + "Z"
    meta_path = _inv_dir(investigation_id) / _META_FILE
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state(investigation_id: str) -> Optional[Dict[str, Any]]:
    """Load full state from state.json. Returns None if not found."""
    state_path = _inv_dir(investigation_id) / _STATE_FILE
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_state(investigation_id: str, state: Dict[str, Any]) -> None:
    """Persist state to state.json and update meta.updated_at and meta.version."""
    d = _inv_dir(investigation_id)
    d.mkdir(parents=True, exist_ok=True)
    state_path = d / _STATE_FILE
    # Serialize; handle non-JSON-serializable (e.g. datetime)
    def _serialize(obj: Any) -> Any:
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_serialize(x) for x in obj]
        return obj
    payload = _serialize(state)
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path = d / _META_FILE
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {"id": investigation_id, "name": investigation_id, "batches": [], "version": 1}
    meta["updated_at"] = datetime.utcnow().isoformat() + "Z"
    meta["version"] = state.get("version", meta.get("version", 1))
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def append_batch(
    investigation_id: str,
    batch_id: str,
    doc_count: int,
    job_id: Optional[str] = None,
    entity_count_before: Optional[int] = None,
    entity_count_after: Optional[int] = None,
) -> None:
    """Append a batch entry to meta.batches."""
    meta_path = _inv_dir(investigation_id) / _META_FILE
    if not meta_path.exists():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    batches = meta.get("batches", [])
    batches.append({
        "batch_id": batch_id,
        "added_at": datetime.utcnow().isoformat() + "Z",
        "doc_count": doc_count,
        "job_id": job_id,
        "entity_count_before": entity_count_before,
        "entity_count_after": entity_count_after,
    })
    meta["batches"] = batches[-100:]
    meta["updated_at"] = datetime.utcnow().isoformat() + "Z"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
