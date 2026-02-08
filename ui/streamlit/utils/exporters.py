"""Export helpers (JSON, CSV)."""
import json
from typing import Any, List, Dict


def entities_to_json(entities: List[Dict[str, Any]]) -> str:
    return json.dumps(entities, ensure_ascii=False, indent=2)


def entities_to_csv(entities: List[Dict[str, Any]]) -> str:
    if not entities:
        return "entity_id,text,entity_type,confidence\n"
    keys = list(entities[0].keys()) if isinstance(entities[0], dict) else []
    lines = [",".join(str(e.get(k, "")) for k in keys) for e in entities]
    return "\n".join([",".join(keys)] + lines)
