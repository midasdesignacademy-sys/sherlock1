"""
SHERLOCK - FastAPI backend: health, investigate, events (polling + SSE), WebSocket.
"""

import uuid
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

from core.monitors import ActivityMonitor
from core.graph_enhanced import run_monitored_investigation

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # shutdown if needed


app = FastAPI(title="SHERLOCK API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


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
    """Hybrid search (vector + graph). Body: {"query": "...", "run_id": "..." (optional), "n_results": 10}."""
    body = body or {}
    query = body.get("query", "").strip()
    if not query:
        return {"results": [], "error": "query required"}
    run_id = body.get("run_id")
    n_results = min(50, max(1, int(body.get("n_results", 10))))
    state: Dict[str, Any] = {}
    if run_id:
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
