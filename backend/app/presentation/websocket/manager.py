"""
presentation/websocket/manager.py — WebSocket connection manager.

Manages active WebSocket connections and broadcasts GPS updates to all clients.
"""

import logging
import json
from typing import List, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket client connections.

    Handles:
    - Client connection tracking
    - Broadcast to all connected clients
    - Graceful disconnect handling
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and track new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[WebSocket] New connection. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove disconnected client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"[WebSocket] Disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict) -> None:
        """
        Broadcast message to all connected clients.

        🔴 Called on every GPS update (~1 sec).
        """
        if not self.active_connections:
            return

        message_json = json.dumps(message)

        # Track failed connections to clean up
        failed = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"[WebSocket] Broadcast error: {e}")
                failed.append(connection)

        # Clean up failed connections
        for conn in failed:
            await self.disconnect(conn)

    async def broadcast_to_shipper(self, shipper_id: str, message: dict) -> None:
        """
        Broadcast message to specific shipper updates.

        Clients can subscribe to specific shippers.
        """
        message_json = json.dumps(message)

        failed = []
        for connection in self.active_connections:
            try:
                # In practice, clients would track which shippers they care about
                await connection.send_text(message_json)
            except Exception as e:
                logger.debug(f"[WebSocket] Send error: {e}")
                failed.append(connection)

        for conn in failed:
            await self.disconnect(conn)

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)


# Global manager instance
ws_manager = ConnectionManager()
