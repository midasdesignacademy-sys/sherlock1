"""
SHERLOCK - WebSocket endpoint for real-time activity events.
"""

import asyncio
import json
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
            await websocket.send_json({"events": events})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
