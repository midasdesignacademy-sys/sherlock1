"""
SHERLOCK - FastAPI backend: health, investigate, events (polling + SSE), WebSocket.
"""

import json
import re
import uuid
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

from core.config import settings
from core.monitors import ActivityMonitor
from core.graph_enhanced import run_monitored_investigation
from core.investigation_store import (
    create as inv_create,
    list_all as inv_list,
    get_meta,
    load_state as inv_load_state,
    save_state as inv_save_state,
    append_batch as inv_append_batch,
    update_meta as inv_update_meta,
)
from core.memory import consolidate_memories
from core.state import create_initial_state
from core.graph import create_sherlock_graph

# In-memory store for last run state (keyed by run_id)
_runs: Dict[str, Dict[str, Any]] = {}
_runs_lock = threading.Lock()


def _run_investigation(run_id: str, uploads_path: str) -> None:
    try:
        state = run_monitored_investigation(documents_path=uploads_path)
        with _runs_lock:
            _runs[run_id] = {
                "status": "completed",
                "state": {
                    "document_metadata_count": len(state.get("document_metadata", {})),
                    "entities_count": len(state.get("entities", {})),
                    "relationships_count": len(state.get("relationships", [])),
                    "current_step": state.get("current_step"),
                    "odos_status": state.get("odos_status"),
                },
                "state_full": state,
            }
    except Exception as e:
        with _runs_lock:
            _runs[run_id] = {"status": "failed", "error": str(e)}


def _run_investigation_and_save(investigation_id: str, uploads_path: str) -> None:
    """Run pipeline and persist state to investigation store (Sprint 1)."""
    try:
        state = run_monitored_investigation(documents_path=uploads_path, investigation_id=investigation_id)
        state["version"] = state.get("version", 1)
        state["last_updated"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
        inv_save_state(investigation_id, dict(state))
        inv_append_batch(
            investigation_id,
            batch_id=str(__import__("uuid").uuid4()),
            doc_count=len(state.get("document_metadata", {})),
            entity_count_after=len(state.get("entities", {})),
        )
        consolidate_memories(investigation_id, state)
    except Exception as e:
        from loguru import logger
        logger.exception(f"Investigation run failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # shutdown if needed


app = FastAPI(title="SHERLOCK API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def root() -> Dict[str, Any]:
    """API root: info and links."""
    return {
        "name": "SHERLOCK API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    """Status and optional Neo4j/Chroma check."""
    result: Dict[str, Any] = {"status": "ok"}
    try:
        from knowledge_graph.neo4j_client import Neo4jClient
        c = Neo4jClient()
        c.connect()
        c.close()
        result["neo4j"] = "connected"
    except Exception as e:
        result["neo4j"] = str(e)
    return result


@app.post("/investigate")
def investigate(body: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Start investigation in background; returns run_id. Body: {"uploads_path": "..."}."""
    uploads_path = (body or {}).get("uploads_path", "")
    run_id = str(uuid.uuid4())
    t = threading.Thread(target=_run_investigation, args=(run_id, uploads_path or None))
    t.daemon = True
    t.start()
    return {"run_id": run_id}


@app.get("/runs")
def list_runs() -> Dict[str, Any]:
    """List run IDs and status (Fase 5 - stable API)."""
    with _runs_lock:
        runs = [
            {"run_id": rid, "status": d.get("status", "unknown")}
            for rid, d in _runs.items()
        ]
    return {"runs": runs}


@app.post("/investigations")
def post_investigations(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create new investigation. Body: { name?, uploads_path? }. If uploads_path given, run pipeline in background and save state."""
    body = body or {}
    name = body.get("name")
    uploads_path = body.get("uploads_path")
    inv_id = inv_create(name=name)
    if uploads_path:
        t = threading.Thread(target=_run_investigation_and_save, args=(inv_id, uploads_path))
        t.daemon = True
        t.start()
    return {"investigation_id": inv_id, "status": "created", "message": "Run in progress" if uploads_path else "Created"}


@app.get("/investigations")
def get_investigations() -> Dict[str, Any]:
    """List all investigations (meta)."""
    items = inv_list()
    return {"investigations": items}


@app.get("/investigations/{investigation_id}")
def get_investigation(investigation_id: str) -> Dict[str, Any]:
    """Get investigation meta and summary (doc_count, entity_count from last state)."""
    meta = get_meta(investigation_id)
    if not meta:
        return {"error": "not_found", "investigation_id": investigation_id}
    state = inv_load_state(investigation_id)
    summary = {}
    if state:
        summary["document_count"] = len(state.get("document_metadata", {}))
        summary["entity_count"] = len(state.get("entities", {})) if isinstance(state.get("entities"), dict) else 0
        summary["relationship_count"] = len(state.get("relationships", []))
        summary["current_step"] = state.get("current_step")
        summary["odos_status"] = state.get("odos_status")
    return {"meta": meta, "summary": summary}


@app.get("/investigations/{investigation_id}/state")
def get_investigation_state(investigation_id: str, full: bool = Query(True, description="Full state")) -> Dict[str, Any]:
    """Get investigation state (full or summary)."""
    state = inv_load_state(investigation_id)
    if not state:
        return {"error": "not_found", "investigation_id": investigation_id}
    if full:
        return {"state": state}
    return {
        "state": {
            "document_metadata_count": len(state.get("document_metadata", {})),
            "entities_count": len(state.get("entities", {})) if isinstance(state.get("entities"), dict) else 0,
            "relationships_count": len(state.get("relationships", [])),
            "current_step": state.get("current_step"),
            "odos_status": state.get("odos_status"),
            "version": state.get("version"),
        }
    }


@app.get("/investigations/{investigation_id}/graph")
def get_investigation_graph(investigation_id: str) -> Dict[str, Any]:
    """Get graph for Cytoscape: nodes from entities, edges from relationships."""
    state = inv_load_state(investigation_id)
    if not state:
        return {"error": "not_found", "investigation_id": investigation_id}
    entities = state.get("entities") or {}
    relationships = state.get("relationships") or []
    if not isinstance(entities, dict):
        entities = {}
    if not isinstance(relationships, list):
        relationships = []
    nodes = []
    for eid, ent in entities.items():
        d = ent if isinstance(ent, dict) else (getattr(ent, "model_dump", lambda: {})() if hasattr(ent, "model_dump") else {})
        label = (d.get("text") or eid)[:50]
        nodes.append({
            "data": {
                "id": eid,
                "label": label,
                "entity_type": d.get("entity_type"),
                "doc_id": d.get("doc_id"),
                "text": d.get("text"),
                **{k: v for k, v in d.items() if k not in ("text", "entity_type", "doc_id") and not callable(v)},
            }
        })
    edges = []
    for i, r in enumerate(relationships):
        rd = r if isinstance(r, dict) else (getattr(r, "model_dump", lambda: {})() if hasattr(r, "model_dump") else {})
        src = rd.get("source_entity_id")
        tgt = rd.get("target_entity_id")
        if src and tgt:
            edges.append({
                "data": {
                    "id": f"e{i}_{src}_{tgt}",
                    "source": src,
                    "target": tgt,
                    "relationship_type": rd.get("relationship_type"),
                    **{k: v for k, v in rd.items() if k not in ("source_entity_id", "target_entity_id", "relationship_type") and not callable(v)},
                }
            })
    return {"elements": {"nodes": nodes, "edges": edges}}


def _uploads_dir_for(investigation_id: str) -> Path:
    """Directory for uploaded files of an investigation."""
    d = settings.UPLOADS_DIR / investigation_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sanitize_filename(name: str) -> str:
    """Remove path components and unsafe chars."""
    name = Path(name).name if "/" in name or "\\" in name else name
    name = re.sub(r"[^\w\s\-\.]", "_", name)[:200]
    return name or "file"


@app.post("/investigations/{investigation_id}/uploads")
async def post_investigation_uploads(
    investigation_id: str,
    files: List[UploadFile] = File(..., description="One or more files"),
    description: Optional[str] = Form(None, description="Description applied to all files"),
    descriptions: Optional[str] = Form(None, description='JSON object: {"filename": "desc"}'),
) -> Dict[str, Any]:
    """Upload files for an investigation. Saves to data/uploads/{investigation_id}/ and optional descriptions.json."""
    meta = get_meta(investigation_id)
    if not meta:
        return {"error": "not_found", "investigation_id": investigation_id}
    upload_dir = _uploads_dir_for(investigation_id)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    allowed = set(s.lower() for s in settings.SUPPORTED_FORMATS)
    uploaded_names: List[str] = []
    desc_by_file: Dict[str, str] = {}
    if description:
        desc_by_file["*"] = description
    if descriptions:
        try:
            desc_by_file.update(json.loads(descriptions))
        except Exception:
            pass
    # Load existing descriptions to merge
    desc_path = upload_dir / "descriptions.json"
    if desc_path.exists():
        try:
            existing = json.loads(desc_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                desc_by_file = {**existing, **desc_by_file}
        except Exception:
            pass
    seen: Dict[str, int] = {}
    for u in files:
        if not u.filename:
            continue
        base_name = _sanitize_filename(u.filename)
        suffix = Path(u.filename).suffix.lower()
        if suffix not in allowed:
            continue
        content = await u.read()
        if len(content) > max_bytes:
            continue
        final_name = base_name
        if final_name in seen:
            seen[final_name] += 1
            final_name = f"{Path(base_name).stem}_{seen[final_name]}{suffix}"
        else:
            seen[final_name] = 0
        dest = upload_dir / final_name
        dest.write_bytes(content)
        uploaded_names.append(final_name)
        if description:
            desc_by_file[final_name] = description
        elif descriptions:
            try:
                d = json.loads(descriptions)
                desc_by_file[final_name] = d.get(final_name) or d.get(u.filename or "", "")
            except Exception:
                pass
    if desc_by_file and "*" in desc_by_file:
        global_desc = desc_by_file.pop("*", "")
        for n in uploaded_names:
            if n not in desc_by_file:
                desc_by_file[n] = global_desc
    if desc_by_file:
        desc_path.write_text(json.dumps(desc_by_file, ensure_ascii=False, indent=2), encoding="utf-8")
    uploads_path = str(upload_dir.resolve())
    files_count = len([x for x in upload_dir.iterdir() if x.is_file() and x.name != "descriptions.json"])
    inv_update_meta(investigation_id, {"uploads_path": uploads_path, "files_count": files_count})
    return {"uploaded": uploaded_names, "total": len(uploaded_names), "uploads_path": uploads_path}


@app.get("/investigations/{investigation_id}/files")
def get_investigation_files(investigation_id: str) -> Dict[str, Any]:
    """List uploaded files and optional descriptions for an investigation."""
    meta = get_meta(investigation_id)
    if not meta:
        return {"error": "not_found", "investigation_id": investigation_id}
    uploads_path = meta.get("uploads_path")
    if not uploads_path:
        return {"files": [], "uploads_path": None}
    upload_dir = Path(uploads_path)
    if not upload_dir.exists():
        return {"files": [], "uploads_path": uploads_path}
    desc_path = upload_dir / "descriptions.json"
    descriptions: Dict[str, str] = {}
    if desc_path.exists():
        try:
            descriptions = json.loads(desc_path.read_text(encoding="utf-8"))
            if not isinstance(descriptions, dict):
                descriptions = {}
        except Exception:
            pass
    files: List[Dict[str, Any]] = []
    for f in upload_dir.iterdir():
        if f.is_file() and f.name != "descriptions.json":
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "description": descriptions.get(f.name),
            })
    files.sort(key=lambda x: x["name"])
    return {"files": files, "uploads_path": uploads_path}


@app.post("/investigations/{investigation_id}/run")
def post_investigation_run(investigation_id: str) -> Dict[str, Any]:
    """Run pipeline for this investigation using its uploads folder. Requires uploads_path in meta."""
    meta = get_meta(investigation_id)
    if not meta:
        return {"error": "not_found", "investigation_id": investigation_id}
    uploads_path = meta.get("uploads_path")
    if not uploads_path or not Path(uploads_path).exists():
        return {"error": "Add files first", "investigation_id": investigation_id}
    t = threading.Thread(target=_run_investigation_and_save, args=(investigation_id, uploads_path))
    t.daemon = True
    t.start()
    return {"status": "running", "investigation_id": investigation_id}


@app.get("/runs/{run_id}")
def get_run(run_id: str, full: bool = Query(False, description="Include full state")) -> Dict[str, Any]:
    """Get run status and state (if completed). Use ?full=1 for full state (hypotheses, report_summary, etc.)."""
    with _runs_lock:
        data = dict(_runs.get(run_id, {"status": "unknown"}))
    if full and isinstance(data.get("state_full"), dict):
        data["state"] = data.pop("state_full", None)
        return data
    if isinstance(data, dict) and "state_full" in data:
        out = {k: v for k, v in data.items() if k != "state_full"}
        return out
    return data


@app.post("/search")
def search(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Hybrid search (vector + graph). Body: {"query": "...", "run_id": "..." or "investigation_id": "...", "n_results": 10}."""
    body = body or {}
    query = body.get("query", "").strip()
    if not query:
        return {"results": [], "error": "query required"}
    run_id = body.get("run_id")
    investigation_id = body.get("investigation_id")
    n_results = min(50, max(1, int(body.get("n_results", 10))))
    state: Dict[str, Any] = {}
    if investigation_id:
        state = inv_load_state(investigation_id) or {}
    elif run_id:
        with _runs_lock:
            data = _runs.get(run_id, {})
            state = data.get("state_full") or {}
    try:
        from rag.hybrid_search import hybrid_search
        results = hybrid_search(query, state, n_results=n_results)
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}


@app.get("/events")
def get_events(n: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
    """Poll recent activity events (for dashboard)."""
    events = ActivityMonitor().get_recent(n)
    return {"events": events}


@app.get("/events/stream")
def events_stream():
    """SSE stream of activity events (polling every 2s)."""
    import time
    import json

    def gen():
        while True:
            events = ActivityMonitor().get_recent(50)
            yield f"data: {json.dumps({'events': events})}\n\n"
            time.sleep(2)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/memory/patterns")
def memory_patterns(pattern_type: Optional[str] = None, min_confidence: float = Query(0.0, ge=0, le=1)) -> Dict[str, Any]:
    """LTM patterns (Fase 5)."""
    try:
        from core.memory import get_memory_manager
        mm = get_memory_manager()
        items = mm.get_patterns(pattern_type=pattern_type, min_confidence=min_confidence)
        return {"patterns": items[-100:]}
    except Exception as e:
        return {"patterns": [], "error": str(e)}


@app.get("/memory/episodes")
def memory_episodes(investigation_id: Optional[str] = None, agent_id: Optional[str] = None, limit: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
    """Episodic memory (Fase 5)."""
    try:
        from core.memory import get_memory_manager
        mm = get_memory_manager()
        items = mm.get_episodes(investigation_id=investigation_id, agent_id=agent_id, limit=limit)
        return {"episodes": items}
    except Exception as e:
        return {"episodes": [], "error": str(e)}


@app.get("/memory/history")
def memory_history(limit: int = Query(20, ge=1, le=100)) -> Dict[str, Any]:
    """Investigation history from LTM (Fase 5)."""
    try:
        from core.memory import get_memory_manager
        mm = get_memory_manager()
        items = mm.get_investigation_history(limit=limit)
        return {"history": items}
    except Exception as e:
        return {"history": [], "error": str(e)}


# WebSocket router mounted in main
from api.websocket import router as ws_router
app.include_router(ws_router, tags=["websocket"])


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8001, reload=False)
