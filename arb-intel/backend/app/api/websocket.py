"""WebSocket handler for real-time updates.

Pushes opportunity updates to connected clients.
"""

import asyncio
import json
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set

from ..core.models import ScanResult
from ..engine import scanner, format_opportunity_json, generate_disclaimer


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and register new connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        async with self._lock:
            self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self.active_connections:
            return

        data = json.dumps(message)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected
        for conn in disconnected:
            await self.disconnect(conn)

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self.active_connections)


# Global connection manager
manager = ConnectionManager()


async def broadcast_scan_result(result: ScanResult):
    """
    Broadcast scan results to all connected clients.

    Called by scanner after each scan cycle.
    """
    message = {
        "type": "scan_result",
        "timestamp": result.timestamp.isoformat(),
        "markets_scanned": result.markets_scanned,
        "scan_duration_ms": result.scan_duration_ms,
        "opportunities_count": len(result.opportunities),
        "opportunities": [
            format_opportunity_json(o)
            for o in result.opportunities[:50]  # Limit to top 50
        ],
    }

    await manager.broadcast(message)


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint handler.

    Sends initial state then listens for commands.
    Commands:
    - ping: Returns pong
    - subscribe: Subscribe to updates (default)
    - unsubscribe: Stop updates
    """
    # Accept all WebSocket connections (CORS handled by proxy)
    await manager.connect(websocket)

    # Register for scan updates
    scanner.register_callback(broadcast_scan_result)

    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "scanner_running": scanner.is_running,
            "opportunities_count": len(scanner.opportunities),
            "disclaimer": generate_disclaimer(),
        })

        # Send current opportunities
        if scanner.opportunities:
            await websocket.send_json({
                "type": "initial_opportunities",
                "opportunities": [
                    format_opportunity_json(o)
                    for o in scanner.opportunities[:50]
                ],
            })

        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                cmd = message.get("command", "")

                if cmd == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                elif cmd == "get_opportunities":
                    await websocket.send_json({
                        "type": "opportunities",
                        "opportunities": [
                            format_opportunity_json(o)
                            for o in scanner.opportunities[:50]
                        ],
                    })

                elif cmd == "get_stats":
                    await websocket.send_json({
                        "type": "stats",
                        "scanner_running": scanner.is_running,
                        "markets_count": len(scanner.markets),
                        "opportunities_count": len(scanner.opportunities),
                        "connections": manager.connection_count,
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
        # Note: Don't unregister callback as other connections may need it
