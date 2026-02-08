"""
SHERLOCK - WebSocket endpoint for real-time activity events.
"""

import asyncio
from fastapi import APIRouter
from fastapi import WebSocket, WebSocketDisconnect

from core.monitors import ActivityMonitor

router = APIRouter()


@router.websocket("/ws")
async def websocket_events(websocket: WebSocket) -> None:
    """Send activity events every 2 seconds until client disconnects."""
    await websocket.accept()
    try:
        while True:
            events = ActivityMonitor().get_recent(50)
            await websocket.send_json({"type": "activity", "events": events})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@router.websocket("/ws/investigation/{investigation_id}")
async def websocket_investigation(websocket: WebSocket, investigation_id: str) -> None:
    """Send activity events for a single investigation every 1-2s. For Pipeline Monitor."""
    await websocket.accept()
    try:
        while True:
            events = ActivityMonitor().get_recent(100, investigation_id=investigation_id)
            await websocket.send_json({
                "type": "activity",
                "investigation_id": investigation_id,
                "events": events,
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
